import type { SummaryItem } from "./types";

export type SortOrder = "asc" | "desc";

/** 在庫数で並び替える（同数なら商品コード順）。元の配列は変えない。 */
export function sortSummaryItems(items: SummaryItem[], order: SortOrder): SummaryItem[] {
  const sign = order === "asc" ? 1 : -1;
  return [...items].sort((a, b) => sign * (a.stock - b.stock) || a.sku.localeCompare(b.sku));
}
