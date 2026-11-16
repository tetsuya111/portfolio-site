"use client";

import { useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/AppShell";
import { ApiError, apiFetch, toQuery } from "@/lib/api";
import { formatDateTime, formatNumber, movementTypeLabel } from "@/lib/format";
import type { HistoryPage, MovementType, Product } from "@/lib/types";

const PAGE_SIZE = 20;

interface Filters {
  product_id: string;
  type: "" | MovementType;
  date_from: string;
  date_to: string;
}

const EMPTY: Filters = { product_id: "", type: "", date_from: "", date_to: "" };

function History() {
  const [products, setProducts] = useState<Product[]>([]);
  const [draft, setDraft] = useState<Filters>(EMPTY);
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<HistoryPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Product[]>("/products")
      .then(setProducts)
      .catch(() => setProducts([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    apiFetch<HistoryPage>(
      `/inventory/history${toQuery({ ...filters, limit: PAGE_SIZE, offset })}`,
    )
      .then((p) => {
        if (cancelled) return;
        setPage(p);
        setError(null);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof ApiError ? e.message : "読み込みに失敗しました。");
      });
    return () => {
      cancelled = true;
    };
  }, [filters, offset]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setFilters(draft);
  }

  function handleReset() {
    setDraft(EMPTY);
    setOffset(0);
    setFilters(EMPTY);
  }

  const set = (key: keyof Filters) => (e: { target: { value: string } }) =>
    setDraft((prev) => ({ ...prev, [key]: e.target.value }));

  const total = page?.total ?? 0;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, total);

  return (
    <>
      <form className="toolbar" onSubmit={handleSubmit}>
        <label className="field">
          <span>商品</span>
          <select value={draft.product_id} onChange={set("product_id")}>
            <option value="">すべて</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.sku} {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>区分</span>
          <select value={draft.type} onChange={set("type")}>
            <option value="">すべて</option>
            <option value="in">入庫</option>
            <option value="out">出庫</option>
          </select>
        </label>
        <label className="field">
          <span>開始日</span>
          <input type="date" value={draft.date_from} onChange={set("date_from")} />
        </label>
        <label className="field">
          <span>終了日</span>
          <input type="date" value={draft.date_to} onChange={set("date_to")} />
        </label>
        <button className="button" type="submit">
          絞り込む
        </button>
        <button className="button secondary" type="button" onClick={handleReset}>
          クリア
        </button>
      </form>
      <p className="muted">日付は UTC の日付で絞り込みます。</p>
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      {!page ? (
        <p className="muted">読み込み中…</p>
      ) : page.items.length === 0 ? (
        <p className="muted">データがありません。</p>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>日時</th>
                  <th>区分</th>
                  <th>商品</th>
                  <th className="num">数量</th>
                  <th className="num">記録後の在庫</th>
                  <th>担当</th>
                  <th>備考</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((m) => (
                  <tr key={m.id}>
                    <td>{formatDateTime(m.created_at)}</td>
                    <td>
                      <span className={`badge ${m.type}`}>{movementTypeLabel(m.type)}</span>
                    </td>
                    <td>
                      {m.product_sku} {m.product_name}
                    </td>
                    <td className="num">{formatNumber(m.quantity)}</td>
                    <td className="num">{formatNumber(m.stock_after)}</td>
                    <td>{m.username}</td>
                    <td>{m.note ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pager">
            <span className="muted">
              {formatNumber(total)} 件中 {formatNumber(from)}〜{formatNumber(to)} 件
            </span>
            <button
              className="button secondary small"
              type="button"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              前へ
            </button>
            <button
              className="button secondary small"
              type="button"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              次へ
            </button>
          </div>
        </>
      )}
    </>
  );
}

export default function HistoryPageView() {
  return (
    <AppShell title="入出庫履歴">
      <History />
    </AppShell>
  );
}
