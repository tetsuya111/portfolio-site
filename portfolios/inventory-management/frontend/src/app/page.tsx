"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { BarChart } from "@/components/BarChart";
import { SummaryStats } from "@/components/SummaryStats";
import { ApiError, apiFetch, toQuery } from "@/lib/api";
import { lowStockItems, topStocked } from "@/lib/dashboard";
import { formatDateTime, formatNumber, movementTypeLabel } from "@/lib/format";
import type { HistoryPage, Summary } from "@/lib/types";

const EMPTY = "データがありません。";

function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recent, setRecent] = useState<HistoryPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiFetch<Summary>("/inventory/summary"),
      apiFetch<HistoryPage>(`/inventory/history${toQuery({ limit: 5 })}`),
    ])
      .then(([s, h]) => {
        setSummary(s);
        setRecent(h);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "読み込みに失敗しました。"));
  }, []);

  if (error) return <p className="alert">{error}</p>;
  if (!summary || !recent) return <p className="muted">読み込み中…</p>;

  const low = lowStockItems(summary.items);
  const top = topStocked(summary.items).map((i) => ({ label: `${i.sku} ${i.name}`, value: i.stock }));

  return (
    <div className="grid">
      <SummaryStats summary={summary} />

      <div className="grid cols-2">
        <section className="card">
          <h2>在庫数 上位10商品</h2>
          <BarChart data={top} emptyText={EMPTY} />
        </section>
        <section className="card">
          <h2>在庫が少ない商品</h2>
          {low.length === 0 ? (
            <p className="muted">{summary.items.length === 0 ? EMPTY : "在庫が少ない商品はありません。"}</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>商品</th>
                    <th className="num">在庫数</th>
                    <th className="num">発注点</th>
                  </tr>
                </thead>
                <tbody>
                  {low.map((i) => (
                    <tr key={i.product_id}>
                      <td>
                        {i.sku} {i.name}
                      </td>
                      <td className="num">
                        <span className="badge low">
                          {formatNumber(i.stock)} {i.unit}
                        </span>
                      </td>
                      <td className="num">{formatNumber(i.reorder_point)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <section className="card">
        <div className="toolbar">
          <h2 style={{ margin: 0 }}>直近の入出庫</h2>
          <span className="spacer" />
          <Link href="/inventory/history/">履歴をすべて見る</Link>
        </div>
        {recent.items.length === 0 ? (
          <p className="muted">{EMPTY}</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>日時</th>
                  <th>区分</th>
                  <th>商品</th>
                  <th className="num">数量</th>
                  <th>担当</th>
                </tr>
              </thead>
              <tbody>
                {recent.items.map((m) => (
                  <tr key={m.id}>
                    <td>{formatDateTime(m.created_at)}</td>
                    <td>
                      <span className={`badge ${m.type}`}>{movementTypeLabel(m.type)}</span>
                    </td>
                    <td>
                      {m.product_sku} {m.product_name}
                    </td>
                    <td className="num">{formatNumber(m.quantity)}</td>
                    <td>{m.username}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AppShell title="ダッシュボード">
      <Dashboard />
    </AppShell>
  );
}
