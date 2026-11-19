/** 外部リンクとして使ってよい URL（http/https のみ）を返す。それ以外は null（NFR-3）。 */
export function safeExternalUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : null;
  } catch {
    return null;
  }
}

/** Google マップの検索リンク。 */
export function mapsSearchUrl(name: string, address = ""): string {
  const query = [name, address].filter(Boolean).join(" ");
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

const fmt = (iso: string) => iso.replaceAll("-", "/");

/** 開催期間の表示（例: 2026/12/03 13:00、2026/12/03〜2026/12/05）。 */
export function formatPeriod(start: string, end: string, time?: string | null): string {
  const period = start === end ? fmt(start) : `${fmt(start)}〜${fmt(end)}`;
  return time ? `${period} ${time.slice(0, 5)}` : period;
}

/** 日付を YYYY-MM-DD にする（ローカル時刻）。 */
export function toIsoDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function addDays(date: Date, days: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}
