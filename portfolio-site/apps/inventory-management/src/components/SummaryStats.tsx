// 在庫の集計値（商品数・総在庫数・在庫が少ない商品の数）のカード。

import { formatNumber } from "@/lib/format";
import type { Summary } from "@/lib/types";

export function SummaryStats({ summary }: { summary: Summary }) {
  const stats = [
    { label: "商品数", value: summary.total_products },
    { label: "総在庫数", value: summary.total_stock },
    { label: "在庫が少ない商品", value: summary.low_stock_count },
  ];
  return (
    <section className="grid cols-3" aria-label="集計">
      {stats.map((s) => (
        <div className="card" key={s.label}>
          <div className="stat-label">{s.label}</div>
          <div className="stat-value">{formatNumber(s.value)}</div>
        </div>
      ))}
    </section>
  );
}
