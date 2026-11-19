"use client";

import { type FormEvent, useState } from "react";

import { VenueMap } from "@/components/VenueMap";
import { fetchVenues } from "@/lib/api";
import { addDays, toIsoDate } from "@/lib/format";
import { useFetch } from "@/lib/useFetch";

const DEFAULT_DAYS = 30;

export default function MapPage() {
  const [today] = useState(() => toIsoDate(new Date()));
  const [period, setPeriod] = useState({ from: today, to: addDays(today, DEFAULT_DAYS) });
  const [draft, setDraft] = useState(period);
  const { data, error, loading } = useFetch(
    () => fetchVenues(period.from, period.to),
    `${period.from}_${period.to}`,
  );

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setPeriod(draft);
  };

  return (
    <>
      <h1>地図でイベントを探す</h1>
      <form className="search-form card" onSubmit={submit}>
        <label className="field">
          開始日
          <input
            type="date"
            required
            value={draft.from}
            onChange={(e) => setDraft((d) => ({ ...d, from: e.target.value }))}
          />
        </label>
        <label className="field">
          終了日
          <input
            type="date"
            required
            min={draft.from}
            value={draft.to}
            onChange={(e) => setDraft((d) => ({ ...d, to: e.target.value }))}
          />
        </label>
        <div>
          <button type="submit">この期間で表示</button>
        </div>
      </form>
      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">読み込み中…</p>}
      {data && !loading && <VenueMap key={`${period.from}_${period.to}`} venues={data} />}
    </>
  );
}
