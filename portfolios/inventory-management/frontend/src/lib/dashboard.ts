// ダッシュボードの表示用の集計。

import { sortSummaryItems } from "./sort";
import type { SummaryItem } from "./types";

/** 在庫数の多い順に上位 n 件。 */
export function topStocked(items: SummaryItem[], n = 10): SummaryItem[] {
  return sortSummaryItems(items, "desc").slice(0, n);
}

/** 在庫が少ない（発注点以下の）商品を在庫数の少ない順に。 */
export function lowStockItems(items: SummaryItem[]): SummaryItem[] {
  return sortSummaryItems(
    items.filter((i) => i.is_low),
    "asc",
  );
}
