// バックエンド API の呼び出し（fetch の薄いラッパー）。

import type {
  Cosplayer,
  CosplayerDetail,
  CosplayerQuery,
  EventDetail,
  EventQuery,
  EventSummary,
  Page,
  VenueWithEvents,
} from "./types";

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Params = Record<string, string | number | undefined | null>;

function buildUrl(path: string, params: Params = {}): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      url.searchParams.set(key, String(value).trim());
    }
  }
  return url.toString();
}

/** DRF のエラー（{"detail": "..."} や {"field": ["..."]}）を1つの文章にする。 */
function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object") {
    const messages = Object.values(body as Record<string, unknown>).flatMap((v) =>
      Array.isArray(v) ? v.map(String) : [String(v)],
    );
    if (messages.length > 0) return messages.join(" ");
  }
  return status === 404 ? "見つかりませんでした。" : `エラーが発生しました（${status}）。`;
}

async function apiGet<T>(path: string, params?: Params): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiError(0, "サーバーに接続できませんでした。時間をおいて再度お試しください。");
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, errorMessage(body, response.status));
  return body as T;
}

export function fetchEvents(query: EventQuery): Promise<Page<EventSummary>> {
  return apiGet("/api/events/", query);
}

export function fetchEvent(id: number): Promise<EventDetail> {
  return apiGet(`/api/events/${id}/`);
}

export function fetchVenues(from: string, to: string): Promise<VenueWithEvents[]> {
  return apiGet("/api/venues/", { from, to });
}

export function fetchCosplayers(query: CosplayerQuery): Promise<Page<Cosplayer>> {
  return apiGet("/api/cosplayers/", query);
}

export function fetchCosplayer(id: number): Promise<CosplayerDetail> {
  return apiGet(`/api/cosplayers/${id}/`);
}
