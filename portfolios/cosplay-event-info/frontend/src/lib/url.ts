// 外部リンクの安全確認と Google マップの URL（NF-5・MAP-2・MAP-3）。

import type { Venue } from "./types";

/** http(s) の絶対 URL だけを返す。それ以外（javascript: など）は null。 */
export function safeHttpUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? value : null;
  } catch {
    return null;
  }
}

/** API キー不要の埋め込み地図（iframe 用）。 */
export function googleMapsEmbedUrl(query: string): string {
  return `https://www.google.com/maps?q=${encodeURIComponent(query)}&output=embed`;
}

/** Google マップで開くリンク（Maps URLs）。 */
export function googleMapsSearchUrl(query: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

/** 地図の検索語。会場があれば会場名と住所、なければ取得元の表記。 */
export function venueQuery(venue: Venue | null, locationRaw: string): string {
  if (venue) return `${venue.name} ${venue.address}`.trim();
  return locationRaw.trim();
}

const SNS_LABELS: [string, string][] = [
  ["x.com", "X"],
  ["twitter.com", "X"],
  ["instagram.com", "Instagram"],
  ["youtube.com", "YouTube"],
  ["tiktok.com", "TikTok"],
  ["facebook.com", "Facebook"],
  ["threads.net", "Threads"],
  ["threads.com", "Threads"],
];

export function snsLabel(value: string): string {
  try {
    const host = new URL(value).hostname.toLowerCase();
    const found = SNS_LABELS.find(([domain]) => host === domain || host.endsWith(`.${domain}`));
    return found ? found[1] : host;
  } catch {
    return value;
  }
}
