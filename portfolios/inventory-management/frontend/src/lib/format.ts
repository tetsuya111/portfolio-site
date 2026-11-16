// 画面表示用の整形。

import type { MovementType } from "./types";

const numberFormat = new Intl.NumberFormat("ja-JP");
const dateTimeFormat = new Intl.DateTimeFormat("ja-JP", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatNumber(n: number): string {
  return numberFormat.format(n);
}

/** ISO 8601 の日時をブラウザのローカル時刻で表示する。 */
export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return dateTimeFormat.format(date);
}

export function movementTypeLabel(type: MovementType): "入庫" | "出庫" {
  return type === "in" ? "入庫" : "出庫";
}
