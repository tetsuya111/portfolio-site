"use client";

import type { Usage } from "@/lib/types";

/** 残りが少ないとみなす割合。色だけでなくテキストでも知らせる。 */
const LOW_PERCENT = 10;

/**
 * 今日あとどれくらい使えるかを割合で表示する。
 * 専門用語（トークン）と実数は出さない。取得できていないときは何も表示しない。
 */
export function UsageIndicator({ usage }: { usage: Usage | null }) {
  if (!usage) return null;
  if (usage.unlimited) {
    return (
      <p role="status" className="px-2 text-xs text-stone-500">
        今日の残り 制限なし
      </p>
    );
  }
  const percent = usage.remaining_percent ?? 0;
  const low = percent < LOW_PERCENT;
  return (
    <p role="status" className={"px-2 text-xs " + (low ? "font-medium text-amber-700" : "text-stone-500")}>
      今日の残り {percent}%{low && "（少なくなっています）"}
    </p>
  );
}
