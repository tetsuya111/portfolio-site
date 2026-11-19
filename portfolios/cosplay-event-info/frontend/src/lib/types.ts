// バックエンド API のレスポンスの型（backend/catalog/serializers.py と対応）。

export type Venue = {
  id: number;
  name: string;
  prefecture: string;
  address: string;
};

export type Source = {
  url: string;
  fetched_at: string;
};

export type EventSummary = {
  id: number;
  name: string;
  url: string;
  location_raw: string;
  venue: Venue | null;
  start_date: string;
  end_date: string;
  notes: string;
  source_url: string;
};

export type EventDetail = EventSummary & { sources: Source[] };

export type VenueWithEvents = Venue & {
  event_count: number;
  events: Pick<EventSummary, "id" | "name" | "start_date" | "end_date">[];
};

export type Cosplayer = {
  id: number;
  name: string;
  sns_links: string[];
  career: string;
  description: string;
  notes: string;
  source_url: string;
};

export type CosplayerDetail = Cosplayer & { sources: Source[] };

export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type EventQuery = {
  q?: string;
  from?: string;
  to?: string;
  prefecture?: string;
  page?: number;
};

export type CosplayerQuery = {
  q?: string;
  page?: number;
};
