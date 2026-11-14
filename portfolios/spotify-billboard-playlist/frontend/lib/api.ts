// バックエンド(FastAPI)の呼び出し。Next.js の rewrites により同一オリジンの相対パスで届く。

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** OAuth はバックエンドへのページ遷移で開始する（fetch ではなくリンクで使う）。 */
export const LOGIN_PATH = "/auth/login";

/** csrf_token は状態を変えるリクエストに X-CSRF-Token ヘッダーで送り返す。 */
export type Me =
  | { authenticated: false }
  | { authenticated: true; id: string; display_name: string; csrf_token: string };

export type Track = { title: string; artist: string };
export type ChartTrack = Track & { rank: number };
/** title はページの <title>（サイト名を除く）。古いバックエンドは返さないため省略可。 */
export type Chart = { id: number; url: string; title?: string; tracks: ChartTrack[] };
export type PlaylistResult = { playlist_id: string; url: string; added: number; not_found: Track[] };

function detailMessage(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : null))
      .filter(Boolean);
    if (messages.length) return `入力が正しくありません: ${messages.join(" / ")}`;
  }
  return null;
}

/** 直近の getMe で受け取った CSRF トークン（未ログインなら null）。 */
let csrfToken: string | null = null;

async function request<T>(path: string, init?: RequestInit, retryOnForbidden = true): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const unsafe = method !== "GET" && method !== "HEAD";
  const headers = new Headers(init?.headers);
  if (unsafe && csrfToken) headers.set("X-CSRF-Token", csrfToken);
  let res: Response;
  try {
    res = await fetch(path, { credentials: "same-origin", ...init, headers });
  } catch {
    throw new ApiError(0, "サーバーに接続できませんでした");
  }
  if (res.status === 204) return undefined as T;
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 403 && unsafe && retryOnForbidden) {
      // 別タブでの再ログインなどでトークンが古い（または未取得の）可能性がある。
      // 取り直してトークンが変わったときだけ1回再送する（403 は処理前に拒否されるので再送しても安全）
      const before = csrfToken;
      await getMe().catch(() => null);
      if (csrfToken && csrfToken !== before) return request<T>(path, init, false);
    }
    const detail = body && typeof body === "object" && "detail" in body ? body.detail : null;
    throw new ApiError(res.status, detailMessage(detail) ?? `エラーが発生しました（HTTP ${res.status}）`);
  }
  return body as T;
}

function postJson<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getMe(): Promise<Me> {
  const me = await request<Me>("/api/me");
  csrfToken = me.authenticated ? me.csrf_token : null;
  return me;
}

export async function logout(): Promise<void> {
  await request<void>("/auth/logout", { method: "POST" });
  csrfToken = null;
}

export function fetchChart(url: string): Promise<Chart> {
  return postJson<Chart>("/api/charts", { url });
}

export function createPlaylist(name: string, tracks: Track[]): Promise<PlaylistResult> {
  return postJson<PlaylistResult>("/api/playlists", { name, tracks });
}
