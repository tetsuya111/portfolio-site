// 日付の表示と計算（API の日付は YYYY-MM-DD）。

export function formatDate(iso: string): string {
  return iso.replaceAll("-", "/");
}

export function formatDateRange(start: string, end: string): string {
  return start === end ? formatDate(start) : `${formatDate(start)} 〜 ${formatDate(end)}`;
}

/** ローカル時刻の日付を YYYY-MM-DD にする。 */
export function toIsoDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  return toIsoDate(new Date(y, m - 1, d + days));
}
