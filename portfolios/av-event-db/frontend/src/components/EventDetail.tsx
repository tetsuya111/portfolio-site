"use client";

import { useEffect, useState } from "react";

import { ApiError, fetchEvent } from "@/lib/api";
import { formatPeriod, mapsSearchUrl, safeExternalUrl } from "@/lib/format";
import type { EventDetail as EventDetailData } from "@/lib/types";

function ExternalLink({ href, children }: { href: string | null; children: string }) {
  const safe = safeExternalUrl(href);
  if (!safe) return <>{children}</>;
  return (
    <a href={safe} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
}

/** イベントの詳細（REQ-5.5）。取得したテキストは React のテキストとして描画する（NFR-3）。 */
export function EventDetail({ id }: { id: number }) {
  const [state, setState] = useState<{ id: number; data?: EventDetailData; error?: string }>();

  useEffect(() => {
    let cancelled = false;
    fetchEvent(id)
      .then((data) => !cancelled && setState({ id, data }))
      .catch((e: unknown) => {
        if (cancelled) return;
        setState({ id, error: e instanceof ApiError ? e.message : "読み込みに失敗しました。" });
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const current = state?.id === id ? state : undefined;
  if (!current) return <p className="muted">読み込み中…</p>;
  if (current.error || !current.data) return <p className="alert">{current.error}</p>;
  const e = current.data;
  const official = safeExternalUrl(e.url);

  return (
    <article className="card">
      <h1>{e.title}</h1>
      <dl className="detail-list">
        <dt>日時</dt>
        <dd>{formatPeriod(e.start_date, e.end_date, e.start_time)}</dd>
        <dt>出演</dt>
        <dd>{e.actresses.length > 0 ? e.actresses.join("、") : "—"}</dd>
        <dt>開催場所</dt>
        <dd>
          {e.venue ? (
            <>
              {e.venue.name}
              {e.venue.address && ` ${e.venue.address}`}{" "}
              <a
                href={mapsSearchUrl(e.venue.name, e.venue.address)}
                target="_blank"
                rel="noopener noreferrer"
              >
                Google マップで開く
              </a>
            </>
          ) : (
            e.raw_venue || "—"
          )}
        </dd>
        <dt>リンク</dt>
        <dd>
          {official ? (
            <a href={official} target="_blank" rel="noopener noreferrer">
              {official}
            </a>
          ) : (
            "—"
          )}
        </dd>
        <dt>概要</dt>
        <dd>{e.summary || "—"}</dd>
        <dt>備考</dt>
        <dd>{e.note || "—"}</dd>
        <dt>取得元</dt>
        <dd>
          <ul>
            {e.sources.map((s) => (
              <li key={s.source_url}>
                <ExternalLink href={s.source_url}>{`${s.source_name}: ${s.source_url}`}</ExternalLink>
              </li>
            ))}
          </ul>
        </dd>
      </dl>
    </article>
  );
}
