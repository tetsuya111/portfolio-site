"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { ApiError, PAGE_SIZE, buildQuery, fetchEvents, type SearchQuery } from "@/lib/api";
import { formatPeriod } from "@/lib/format";
import { PREFECTURES } from "@/lib/prefectures";
import type { EventListItem, Page } from "@/lib/types";

type Props = {
  initialQuery: SearchQuery;
  /** 検索条件が変わったとき（URL への反映に使う） */
  onQueryChange?: (query: SearchQuery) => void;
};

type Loaded = { key: string; data?: Page<EventListItem>; error?: string };

/** イベントの検索フォームと結果一覧（REQ-5）。 */
export function EventSearch({ initialQuery, onQueryChange }: Props) {
  const [form, setForm] = useState({
    q: initialQuery.q ?? "",
    from: initialQuery.from ?? "",
    to: initialQuery.to ?? "",
    prefecture: initialQuery.prefecture ?? "",
  });
  const [query, setQuery] = useState<SearchQuery>({ ...form, page: initialQuery.page ?? 1 });
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const key = buildQuery(query).toString();

  useEffect(() => {
    let cancelled = false;
    fetchEvents(query)
      .then((data) => !cancelled && setLoaded({ key, data }))
      .catch((e: unknown) => {
        if (cancelled) return;
        setLoaded({ key, error: e instanceof ApiError ? e.message : "読み込みに失敗しました。" });
      });
    return () => {
      cancelled = true;
    };
  }, [key, query]);

  function apply(next: SearchQuery) {
    setQuery(next);
    onQueryChange?.(next);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    apply({ ...form, page: 1 });
  }

  const current = loaded?.key === key ? loaded : null;
  const page = query.page ?? 1;
  const totalPages = current?.data ? Math.max(1, Math.ceil(current.data.count / PAGE_SIZE)) : 1;

  return (
    <>
      <form className="card toolbar" role="search" onSubmit={handleSubmit}>
        <label className="field">
          <span>キーワード</span>
          <input
            type="search"
            value={form.q}
            placeholder="イベント名・女優名・会場名"
            onChange={(e) => setForm({ ...form, q: e.target.value })}
          />
        </label>
        <label className="field">
          <span>開始日</span>
          <input
            type="date"
            value={form.from}
            onChange={(e) => setForm({ ...form, from: e.target.value })}
          />
        </label>
        <label className="field">
          <span>終了日</span>
          <input
            type="date"
            value={form.to}
            onChange={(e) => setForm({ ...form, to: e.target.value })}
          />
        </label>
        <label className="field">
          <span>都道府県</span>
          <select
            value={form.prefecture}
            onChange={(e) => setForm({ ...form, prefecture: e.target.value })}
          >
            <option value="">すべて</option>
            {PREFECTURES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="button">
          検索
        </button>
      </form>

      <section aria-live="polite" aria-busy={!current}>
        {!current && <p className="muted">読み込み中…</p>}
        {current?.error && <p className="alert">{current.error}</p>}
        {current?.data && current.data.results.length === 0 && (
          <p className="notice">条件に合うイベントはありません。</p>
        )}
        {current?.data && current.data.results.length > 0 && (
          <>
            <p className="muted">全 {current.data.count} 件</p>
            <ul className="event-list">
              {current.data.results.map((e) => (
                <li key={e.id} className="card event-item">
                  <Link href={`/events/?id=${e.id}`} className="event-title">
                    {e.title}
                  </Link>
                  <div className="event-meta">
                    <span>{formatPeriod(e.start_date, e.end_date, e.start_time)}</span>
                    {e.venue && (
                      <span>
                        {e.venue.name}
                        {e.venue.prefecture && `（${e.venue.prefecture}）`}
                      </span>
                    )}
                    {e.actresses.length > 0 && <span>出演: {e.actresses.join("、")}</span>}
                  </div>
                </li>
              ))}
            </ul>
            <nav className="pager" aria-label="ページ送り">
              <button
                type="button"
                className="button secondary small"
                disabled={page <= 1}
                onClick={() => apply({ ...query, page: page - 1 })}
              >
                前へ
              </button>
              <span>
                {page} / {totalPages}
              </span>
              <button
                type="button"
                className="button secondary small"
                disabled={!current.data.next}
                onClick={() => apply({ ...query, page: page + 1 })}
              >
                次へ
              </button>
            </nav>
          </>
        )}
      </section>
    </>
  );
}
