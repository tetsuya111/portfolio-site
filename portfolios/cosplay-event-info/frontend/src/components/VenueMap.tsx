"use client";

import Link from "next/link";
import { useState } from "react";

import { formatDateRange } from "@/lib/format";
import type { VenueWithEvents } from "@/lib/types";
import { googleMapsEmbedUrl, googleMapsSearchUrl, venueQuery } from "@/lib/url";

import { ExternalLink } from "./ExternalLink";

/** 会場の一覧と、選んだ会場の Google マップ（埋め込み）を表示する（MAP-1・MAP-2）。 */
export function VenueMap({ venues }: { venues: VenueWithEvents[] }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  if (venues.length === 0) {
    return <p className="muted">この期間に開催されるイベントはありません。</p>;
  }
  const selected = venues.find((v) => v.id === selectedId) ?? venues[0];
  const query = venueQuery(selected, selected.name);

  return (
    <div className="map-layout">
      <ul className="card-list" aria-label="会場">
        {venues.map((venue) => (
          <li key={venue.id}>
            <button
              type="button"
              className="venue-button"
              aria-pressed={venue.id === selected.id}
              onClick={() => setSelectedId(venue.id)}
            >
              <strong>{venue.name}</strong>
              <span className="meta">
                {venue.prefecture && <span>{venue.prefecture}</span>}
                <span>{venue.event_count} 件</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      <section className="card" aria-label={`${selected.name}の情報`}>
        <iframe
          className="map-frame"
          title={`${selected.name}の地図`}
          src={googleMapsEmbedUrl(query)}
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
        />
        <p style={{ margin: "8px 0" }}>
          <ExternalLink href={googleMapsSearchUrl(query)}>Google マップで開く</ExternalLink>
        </p>
        <h2>{selected.name}で開催されるイベント</h2>
        <ul>
          {selected.events.map((event) => (
            <li key={event.id}>
              <Link href={`/events/detail/?id=${event.id}`}>{event.name}</Link>{" "}
              <span className="muted">{formatDateRange(event.start_date, event.end_date)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
