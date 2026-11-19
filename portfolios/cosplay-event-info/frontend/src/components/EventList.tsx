import Link from "next/link";

import { formatDateRange } from "@/lib/format";
import type { EventSummary } from "@/lib/types";

export function EventList({ events }: { events: EventSummary[] }) {
  if (events.length === 0) {
    return <p className="muted">該当するイベントはありません。</p>;
  }
  return (
    <ul className="card-list">
      {events.map((event) => (
        <li key={event.id} className="card">
          <p className="card-title">
            <Link href={`/events/detail/?id=${event.id}`}>{event.name}</Link>
          </p>
          <div className="meta">
            <span>{formatDateRange(event.start_date, event.end_date)}</span>
            <span>{event.venue ? event.venue.name : event.location_raw || "場所未定"}</span>
            {event.venue?.prefecture && <span className="badge">{event.venue.prefecture}</span>}
          </div>
          {event.notes && <p className="text-block" style={{ margin: "8px 0 0" }}>{event.notes}</p>}
        </li>
      ))}
    </ul>
  );
}
