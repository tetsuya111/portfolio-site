"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { ApiError, apiFetch } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { sortSummaryItems, type SortOrder } from "@/lib/sort";
import type { Summary } from "@/lib/types";

function StockList() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [keyword, setKeyword] = useState("");
  const [order, setOrder] = useState<SortOrder | null>(null);

  useEffect(() => {
    apiFetch<Summary>("/inventory/summary")
      .then(setSummary)
      .catch((e) => setError(e instanceof ApiError ? e.message : "読み込みに失敗しました。"));
  }, []);

  const rows = useMemo(() => {
    if (!summary) return [];
    const k = keyword.trim().toLowerCase();
    const filtered = k
      ? summary.items.filter(
          (i) => i.sku.toLowerCase().includes(k) || i.name.toLowerCase().includes(k),
        )
      : summary.items;
    return order ? sortSummaryItems(filtered, order) : filtered;
  }, [summary, keyword, order]);

  const nextOrder: SortOrder = order === "asc" ? "desc" : "asc";
  const orderMark = order === "asc" ? " ▲" : order === "desc" ? " ▼" : "";

  if (error) return <p className="alert">{error}</p>;
  if (!summary) return <p className="muted">読み込み中…</p>;
  return (
    <>
      <div className="grid cols-3" style={{ marginBottom: "1rem" }}>
        <div className="card">
          <div className="stat-label">商品数</div>
          <div className="stat-value">{formatNumber(summary.total_products)}</div>
        </div>
        <div className="card">
          <div className="stat-label">総在庫数</div>
          <div className="stat-value">{formatNumber(summary.total_stock)}</div>
        </div>
        <div className="card">
          <div className="stat-label">在庫が少ない商品</div>
          <div className="stat-value">{formatNumber(summary.low_stock_count)}</div>
        </div>
      </div>
      <div className="toolbar">
        <label className="field">
          <span>商品コード・商品名で絞り込み</span>
          <input value={keyword} onChange={(e) => setKeyword(e.target.value)} />
        </label>
        <span className="spacer" />
        <Link className="button" href="/inventory/record/">
          入出庫を登録
        </Link>
      </div>
      {rows.length === 0 ? (
        <p className="muted">データがありません。</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>商品コード</th>
                <th>商品名</th>
                <th className="num" aria-sort={order === "asc" ? "ascending" : order === "desc" ? "descending" : "none"}>
                  <button type="button" className="sort-button" onClick={() => setOrder(nextOrder)}>
                    在庫数{orderMark}
                  </button>
                </th>
                <th className="num">発注点</th>
                <th>状態</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((i) => (
                <tr key={i.product_id}>
                  <td>{i.sku}</td>
                  <td>{i.name}</td>
                  <td className="num">
                    {formatNumber(i.stock)} {i.unit}
                  </td>
                  <td className="num">{formatNumber(i.reorder_point)}</td>
                  <td>{i.is_low ? <span className="badge low">在庫が少ない</span> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export default function InventoryPage() {
  return (
    <AppShell title="在庫一覧">
      <StockList />
    </AppShell>
  );
}
