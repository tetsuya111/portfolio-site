// 横棒グラフ（依存を増やさないよう CSS の幅で描く）。

import { formatNumber } from "@/lib/format";

export interface BarDatum {
  label: string;
  value: number;
}

export function BarChart({
  data,
  emptyText,
  label = "在庫数",
}: {
  data: BarDatum[];
  emptyText: string;
  label?: string;
}) {
  if (data.length === 0) return <p className="muted">{emptyText}</p>;
  const max = Math.max(...data.map((d) => d.value), 0);
  return (
    <ul className="bar-chart" aria-label={`${label}の棒グラフ`}>
      {data.map((d) => {
        const ratio = max > 0 ? Math.round((d.value / max) * 100) : 0;
        return (
          <li key={d.label} className="bar-row">
            <span className="bar-label" title={d.label}>
              {d.label}
            </span>
            <span className="bar-track" aria-hidden="true">
              <span className="bar-fill" data-testid="bar-fill" style={{ width: `${ratio}%`, display: "block" }} />
            </span>
            <span className="bar-value">{formatNumber(d.value)}</span>
          </li>
        );
      })}
    </ul>
  );
}
