"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { ApiError, fetchMapVenues } from "@/lib/api";
import { addDays, formatPeriod, mapsSearchUrl, toIsoDate } from "@/lib/format";
import {
  loadGoogleMaps,
  type MapInstance,
  type MapsLoader,
  type MarkerInstance,
} from "@/lib/googleMaps";
import type { MapVenue } from "@/lib/types";

const DEFAULT_DAYS = 30;

type Props = {
  /** Maps JavaScript API のキー。未設定なら地図の代わりに会場一覧を出す（REQ-6.4） */
  apiKey?: string;
  today?: Date;
  loadMaps?: MapsLoader;
};

type Loaded = { key: string; venues?: MapVenue[]; error?: string };

function VenueCard({ venue }: { venue: MapVenue }) {
  return (
    <li className="card">
      <strong>{venue.name}</strong>
      {venue.address && <span className="muted"> {venue.address}</span>}{" "}
      <a
        href={mapsSearchUrl(venue.name, venue.address)}
        target="_blank"
        rel="noopener noreferrer"
      >
        Google マップで開く
      </a>
      <ul>
        {venue.events.map((e) => (
          <li key={e.id}>
            {formatPeriod(e.start_date, e.end_date, e.start_time)}{" "}
            <Link href={`/events/?id=${e.id}`}>{e.title}</Link>
          </li>
        ))}
      </ul>
    </li>
  );
}

const hasCoords = (v: MapVenue) => v.latitude !== null && v.longitude !== null;

/** 期間を指定してイベント会場を地図に表示する（REQ-6）。 */
export function EventMap({ apiKey, today = new Date(), loadMaps = loadGoogleMaps }: Props) {
  const [form, setForm] = useState(() => ({
    from: toIsoDate(today),
    to: toIsoDate(addDays(today, DEFAULT_DAYS)),
  }));
  const [period, setPeriod] = useState(form);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<MapInstance | null>(null);
  const markers = useRef<MarkerInstance[]>([]);
  const key = `${period.from}|${period.to}`;

  useEffect(() => {
    let cancelled = false;
    fetchMapVenues(period.from, period.to)
      .then((venues) => !cancelled && setLoaded({ key, venues }))
      .catch((e: unknown) => {
        if (cancelled) return;
        setLoaded({ key, error: e instanceof ApiError ? e.message : "読み込みに失敗しました。" });
      });
    return () => {
      cancelled = true;
    };
  }, [key, period]);

  const current = loaded?.key === key ? loaded : null;
  const venues = current?.venues;

  useEffect(() => {
    if (!apiKey || !venues || !container.current) return;
    const el = container.current;
    let cancelled = false;
    loadMaps(apiKey)
      .then((maps) => {
        if (cancelled) return;
        map.current ??= new maps.Map(el, { center: { lat: 35.68, lng: 139.76 }, zoom: 5 });
        markers.current.forEach((m) => m.setMap(null));
        const bounds = new maps.LatLngBounds();
        markers.current = venues.filter(hasCoords).map((v) => {
          const position = { lat: v.latitude as number, lng: v.longitude as number };
          bounds.extend(position);
          const marker = new maps.Marker({ position, map: map.current!, title: v.name });
          marker.addListener("click", () => setSelectedId(v.id));
          return marker;
        });
        if (markers.current.length > 0) map.current.fitBounds(bounds);
      })
      .catch(() => !cancelled && setMapError("地図を読み込めませんでした。"));
    return () => {
      cancelled = true;
    };
  }, [apiKey, venues, loadMaps]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSelectedId(null);
    setPeriod(form);
  }

  const showMap = Boolean(apiKey) && !mapError;
  const listed = venues ? (showMap ? venues.filter((v) => !hasCoords(v)) : venues) : [];
  const selected = venues?.find((v) => v.id === selectedId);

  return (
    <>
      <form className="card toolbar" onSubmit={handleSubmit}>
        <label className="field">
          <span>開始日</span>
          <input
            type="date"
            required
            value={form.from}
            onChange={(e) => setForm({ ...form, from: e.target.value })}
          />
        </label>
        <label className="field">
          <span>終了日</span>
          <input
            type="date"
            required
            value={form.to}
            onChange={(e) => setForm({ ...form, to: e.target.value })}
          />
        </label>
        <button type="submit" className="button">
          表示
        </button>
      </form>

      {!apiKey && (
        <p className="notice">地図のAPIキーが設定されていないため、会場を一覧で表示しています。</p>
      )}
      {mapError && <p className="alert">{mapError}会場を一覧で表示しています。</p>}
      {showMap && <div ref={container} className="map-canvas" role="region" aria-label="会場の地図" />}

      <section aria-live="polite">
        {!current && <p className="muted">読み込み中…</p>}
        {current?.error && <p className="alert">{current.error}</p>}
        {venues && venues.length === 0 && (
          <p className="notice">期間内に開催されるイベントはありません。</p>
        )}
        {selected && (
          <>
            <h2>選択した会場</h2>
            <ul className="venue-list">
              <VenueCard venue={selected} />
            </ul>
          </>
        )}
        {listed.length > 0 && (
          <>
            <h2>{showMap ? "地図に表示できない会場" : "会場一覧"}</h2>
            <ul className="venue-list">
              {listed.map((v) => (
                <VenueCard key={v.id} venue={v} />
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  );
}
