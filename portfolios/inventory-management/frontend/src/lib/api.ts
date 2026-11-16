// バックエンド API の呼び出し（fetch の薄いラッパー）とトークンの保存。

import type { MovementType } from "./types";

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(
  /\/$/,
  "",
);
const TOKEN_KEY = "inventory.accessToken";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ---- トークン（localStorage。使えない環境では保存しない） ----

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // プライベートブラウズなどで保存できない場合は、このタブの間だけログイン状態を保つ
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // 何もしない
  }
}

let onUnauthorized: (() => void) | null = null;

/** 401（トークン切れなど）を受け取ったときの処理を登録する。AuthProvider が使う。 */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

// ---- 共通の呼び出し ----

type ApiInit = Omit<RequestInit, "body"> & { json?: unknown; body?: BodyInit };

function errorMessage(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d?.msg === "string" ? d.msg : JSON.stringify(d)))
      .join(" / ");
  }
  return `通信に失敗しました（${status}）。`;
}

async function request<T>(path: string, init: ApiInit, handleUnauthorized: boolean): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let body = init.body;
  if (init.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers, body });
  } catch {
    throw new ApiError(0, "サーバーに接続できません。時間をおいて再度お試しください。");
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!res.ok) {
    if (res.status === 401 && handleUnauthorized) onUnauthorized?.();
    throw new ApiError(res.status, errorMessage(res.status, data));
  }
  return data as T;
}

export function apiFetch<T>(path: string, init: ApiInit = {}): Promise<T> {
  return request<T>(path, init, true);
}

// ---- 認証 ----

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export function login(username: string, password: string): Promise<TokenResponse> {
  const body = new URLSearchParams({ username, password });
  // ログイン失敗の 401 はトークン切れではないため、ログアウト処理を呼ばない。
  return request<TokenResponse>("/auth/login", { method: "POST", body }, false);
}

// ---- クエリ文字列 ----

export function toQuery(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

export function movementPath(type: MovementType): string {
  return `/inventory/${type}`;
}
