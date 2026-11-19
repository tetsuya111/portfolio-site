import type { EventDetail, EventListItem, MapVenue, Page } from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export type SearchQuery = {
  q?: string;
  from?: string;
  to?: string;
  prefecture?: string;
  page?: number;
};

/** 空の値を省いたクエリ文字列を作る（1ページ目は page を付けない）。 */
export function buildQuery(query: SearchQuery): URLSearchParams {
  const params = new URLSearchParams();
  for (const key of ["q", "from", "to", "prefecture"] as const) {
    const value = query[key]?.trim();
    if (value) params.set(key, value);
  }
  if (query.page && query.page > 1) params.set("page", String(query.page));
  return params;
}

export function parseQuery(params: URLSearchParams): SearchQuery {
  const page = Number(params.get("page"));
  return {
    q: params.get("q") ?? "",
    from: params.get("from") ?? "",
    to: params.get("to") ?? "",
    prefecture: params.get("prefecture") ?? "",
    page: Number.isInteger(page) && page > 1 ? page : 1,
  };
}

function errorMessage(body: unknown): string | null {
  if (body && typeof body === "object") {
    const values = Object.values(body as Record<string, unknown>).flat();
    const text = values.filter((v): v is string => typeof v === "string");
    if (text.length > 0) return text.join(" ");
  }
  return null;
}

async function getJson<T>(path: string, params?: URLSearchParams): Promise<T> {
  const qs = params && params.toString() ? `?${params}` : "";
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api${path}${qs}`, { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiError("サーバーに接続できませんでした。", 0);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    if (res.status === 404) throw new ApiError("見つかりませんでした。", 404);
    throw new ApiError(
      (res.status === 400 && errorMessage(body)) || "読み込みに失敗しました。",
      res.status,
    );
  }
  return (await res.json()) as T;
}

export function fetchEvents(query: SearchQuery): Promise<Page<EventListItem>> {
  return getJson("/events/", buildQuery(query));
}

export function fetchEvent(id: number): Promise<EventDetail> {
  return getJson(`/events/${id}/`);
}

export function fetchMapVenues(from: string, to: string): Promise<MapVenue[]> {
  return getJson("/map/venues/", buildQuery({ from, to }));
}
