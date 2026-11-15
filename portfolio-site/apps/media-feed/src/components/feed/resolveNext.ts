import { Content } from "@/lib/api";

/**
 * 次に表示されるものの解決結果。
 * 先読みは kind === "content" のときだけ意味を持つ（広告や末尾では対象が無い）。
 */
export type NextTarget =
  | { kind: "content"; index: number }
  | { kind: "ad"; index: number }
  | { kind: "exhausted" };

/**
 * ある位置から direction 方向へ進んだとき、実際に表示されるものを返す。
 *
 * goTo() が持っていた「同じシリーズを連続で見せない」「N件ごとに広告を挟む」という
 * 判断を副作用なしで再現する。これが無いと、先読み側は「次に何が来るか」を知れない。
 *
 * 状態は変更しない。goTo() と先読みの両方がこの関数を共有する。
 */
export function resolveNextIndex(
  contents: Content[],
  from: number,
  direction: 1 | -1,
  adMap: Map<number, unknown>,
  seriesIdOfCurrent?: string | null,
): NextTarget {
  if (contents.length === 0) return { kind: "exhausted" };

  const target = from + direction;
  if (target < 0) return { kind: "exhausted" };
  if (target >= contents.length) return { kind: "exhausted" };

  const prevSeriesId =
    seriesIdOfCurrent !== undefined
      ? seriesIdOfCurrent
      : contents[from]?.detail?.series_id;

  // 直前と同じシリーズのものは飛ばす。
  let index = target;
  while (index >= 0 && index < contents.length) {
    const sid = contents[index]?.detail?.series_id;
    if (!sid || sid === "-1" || sid !== prevSeriesId) break;
    index += direction;
  }

  if (index < 0 || index >= contents.length) return { kind: "exhausted" };

  // 広告が割り当てられている位置なら、次に出るのはコンテンツではなく広告。
  if (adMap.has(index)) return { kind: "ad", index };
  if (direction === -1 && adMap.has(index + 1)) return { kind: "ad", index: index + 1 };

  return { kind: "content", index };
}

/**
 * 先読み対象のコンテンツを返す。対象が無ければ null。
 */
export function resolvePreloadTarget(
  contents: Content[],
  from: number,
  adMap: Map<number, unknown>,
  seriesIdOfCurrent?: string | null,
): Content | null {
  const next = resolveNextIndex(contents, from, 1, adMap, seriesIdOfCurrent);
  if (next.kind !== "content") return null;
  return contents[next.index] ?? null;
}

/**
 * 回線が細い、または通信量節約が有効なら先読みを控える。
 * 判定できないブラウザでは先読みを行う（既定は速度を優先）。
 */
export function shouldPreload(): boolean {
  if (typeof navigator === "undefined") return false;
  const conn = (navigator as Navigator & {
    connection?: { saveData?: boolean; effectiveType?: string };
  }).connection;
  if (!conn) return true;
  if (conn.saveData) return false;
  if (conn.effectiveType === "2g" || conn.effectiveType === "slow-2g") return false;
  return true;
}
