import { createSseParser, type SseEvent } from "./sse";
import type { User } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const NETWORK_ERROR_MESSAGE = "通信できませんでした。電波の状態を確認して、もう一度お試しください。";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public data: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

// アクセストークンはメモリにのみ保持する（リフレッシュトークンは httpOnly Cookie）
let accessToken: string | null = null;
let refreshing: Promise<User | null> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

async function toApiError(response: Response) {
  const data = await response.json().catch(() => ({}));
  return new ApiError(
    data.code ?? "unknown",
    data.message ?? "うまく処理できませんでした。もう一度お試しください。",
    response.status,
    data,
  );
}

async function rawFetch(path: string, init: RequestInit) {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  try {
    return await fetch(`${BASE_URL}/api${path}`, { ...init, headers, credentials: "include" });
  } catch {
    throw new ApiError("network_error", NETWORK_ERROR_MESSAGE, 0);
  }
}

/** Cookieのリフレッシュトークンからログイン状態を復元する。未ログインなら null。 */
export function restoreSession(): Promise<User | null> {
  refreshing ??= (async () => {
    try {
      const response = await rawFetch("/auth/refresh/", { method: "POST" });
      if (!response.ok) return null;
      const data = await response.json();
      accessToken = data.access;
      return data.user as User;
    } catch {
      return null;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

/** 401のときは1回だけトークンを再発行してやり直す。 */
async function authedFetch(path: string, init: RequestInit) {
  let response = await rawFetch(path, init);
  if (response.status === 401 && (await restoreSession())) {
    response = await rawFetch(path, init);
  }
  return response;
}

export async function api<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const response = await authedFetch(path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw await toApiError(response);
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export function loginWithGoogle(credential: string): Promise<User> {
  return login("/auth/google/", { credential });
}

/** 開発用ログイン。バックエンドが DEBUG かつ ALLOW_DEV_LOGIN のときだけ使える。 */
export function loginForDevelopment(admin: boolean): Promise<User> {
  return login("/auth/dev-login/", { admin });
}

async function login(path: string, body: unknown): Promise<User> {
  const response = await rawFetch(path, { method: "POST", body: JSON.stringify(body) });
  if (!response.ok) throw await toApiError(response);
  const data = await response.json();
  accessToken = data.access;
  return data.user as User;
}

export async function logout() {
  await rawFetch("/auth/logout/", { method: "POST" }).catch(() => undefined);
  accessToken = null;
}

/** メッセージを送信し、SSEのイベントを順に onEvent へ渡す。POSTのため EventSource は使えない。 */
export async function streamMessage(content: string, onEvent: (event: SseEvent) => void) {
  const response = await authedFetch("/conversation/messages/", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
  if (!response.ok || !response.body) throw await toApiError(response);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parse = createSseParser();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      parse(decoder.decode(value, { stream: true })).forEach(onEvent);
    }
  } catch {
    throw new ApiError("network_error", NETWORK_ERROR_MESSAGE, 0);
  }
}
