"use client";

import { type FormEvent, useState } from "react";

import { PREFECTURES } from "@/lib/prefectures";

export type EventSearchValues = { q: string; from: string; to: string; prefecture: string };

type Props = {
  initial: Partial<EventSearchValues>;
  onSearch: (values: EventSearchValues) => void;
};

const EMPTY: EventSearchValues = { q: "", from: "", to: "", prefecture: "" };

export function EventSearchForm({ initial, onSearch }: Props) {
  const [values, setValues] = useState<EventSearchValues>({ ...EMPTY, ...initial });

  const update = (key: keyof EventSearchValues) => (e: { target: { value: string } }) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    onSearch(values);
  };

  const clear = () => {
    setValues(EMPTY);
    onSearch(EMPTY);
  };

  return (
    <form className="search-form card" onSubmit={submit} role="search">
      <label className="field">
        キーワード
        <input
          type="search"
          value={values.q}
          onChange={update("q")}
          placeholder="イベント名・会場・備考"
        />
      </label>
      <label className="field">
        開始日
        <input type="date" value={values.from} onChange={update("from")} />
      </label>
      <label className="field">
        終了日
        <input type="date" value={values.to} onChange={update("to")} />
      </label>
      <label className="field">
        都道府県
        <select value={values.prefecture} onChange={update("prefecture")}>
          <option value="">すべて</option>
          {PREFECTURES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </label>
      <div style={{ display: "flex", gap: 8 }}>
        <button type="submit">検索</button>
        <button type="button" className="secondary" onClick={clear}>
          クリア
        </button>
      </div>
    </form>
  );
}
