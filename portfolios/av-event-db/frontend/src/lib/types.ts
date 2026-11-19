export type VenueSummary = { id: number; name: string; prefecture: string };

export type VenueDetail = VenueSummary & {
  address: string;
  latitude: number | null;
  longitude: number | null;
};

export type EventListItem = {
  id: number;
  title: string;
  start_date: string;
  end_date: string;
  start_time: string | null;
  venue: VenueSummary | null;
  actresses: string[];
};

export type EventSource = { source_name: string; source_url: string };

export type EventDetail = Omit<EventListItem, "venue"> & {
  venue: VenueDetail | null;
  url: string;
  raw_venue: string;
  summary: string;
  note: string;
  sources: EventSource[];
};

export type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export type MapEvent = Pick<EventListItem, "id" | "title" | "start_date" | "end_date" | "start_time">;

export type MapVenue = VenueDetail & { events: MapEvent[] };
