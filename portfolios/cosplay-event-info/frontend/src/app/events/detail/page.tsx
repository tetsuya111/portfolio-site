"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { ExternalLink } from "@/components/ExternalLink";
import { fetchEvent } from "@/lib/api";
import { formatDate, formatDateRange } from "@/lib/format";
import { googleMapsSearchUrl, venueQuery } from "@/lib/url";
import { useFetch } from "@/lib/useFetch";

function EventDetailContent() {
  const id = Number(useSearchParams().get("id"));
  const valid = Number.isInteger(id) && id > 0;
  const { data: event, error, loading } = useFetch(valid ? () => fetchEvent(id) : null, String(id));

  if (!valid) return <p className="error">イベントが指定されていません。</p>;
  if (loading) return <p className="muted">読み込み中…</p>;
  if (error || !event) return <p className="error">{error ?? "イベントが見つかりません。"}</p>;

  const mapQuery = venueQuery(event.venue, event.location_raw);
  return (
    <article>
      <p>
        <Link href="/events/">← イベント一覧へ</Link>
      </p>
      <h1>{event.name}</h1>
      <dl className="detail-table card">
        <dt>開催日</dt>
        <dd>{formatDateRange(event.start_date, event.end_date)}</dd>
        <dt>開催場所</dt>
        <dd>
          {event.venue ? (
            <>
              {event.venue.name}
              {event.venue.prefecture && <span className="badge" style={{ marginLeft: 8 }}>{event.venue.prefecture}</span>}
              {event.venue.address && <div className="muted">{event.venue.address}</div>}
            </>
          ) : (
            event.location_raw || "未定"
          )}
          {mapQuery && (
            <div>
              <ExternalLink href={googleMapsSearchUrl(mapQuery)}>Google マップで開く</ExternalLink>
            </div>
          )}
        </dd>
        {event.venue && event.location_raw && (
          <>
            <dt>取得元の表記</dt>
            <dd>{event.location_raw}</dd>
          </>
        )}
        <dt>リンク</dt>
        <dd>{event.url ? <ExternalLink href={event.url} /> : "なし"}</dd>
        <dt>備考</dt>
        <dd>{event.notes || "なし"}</dd>
      </dl>
      <h2>取得元</h2>
      {event.sources.length === 0 ? (
        <p className="muted">なし</p>
      ) : (
        <ul>
          {event.sources.map((s) => (
            <li key={s.url}>
              <ExternalLink href={s.url} /> <span className="muted">（{formatDate(s.fetched_at.slice(0, 10))} 取得）</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

export default function EventDetailPage() {
  return (
    <Suspense fallback={<p className="muted">読み込み中…</p>}>
      <EventDetailContent />
    </Suspense>
  );
}
