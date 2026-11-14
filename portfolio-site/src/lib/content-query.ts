// 一覧ページの並び順・下書きの除外。Astro のエントリー型に依存しない形にしてテストしやすくする。

const DISPLAY_DATE = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "UTC",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/**
 * 記事の日付を「YYYY/MM/DD」で表示する。frontmatter の日付（`2026-11-13`）は UTC の 0 時として
 * 読み込まれるため、UTC で書式化してビルド環境のタイムゾーンに左右されないようにする。
 */
export function formatDisplayDate(d: Date): string {
  return DISPLAY_DATE.format(d);
}

/** ポートフォリオを date の新しい順に並べる。date が無いものは末尾にタイトル順で並べる。 */
export function sortPortfolios<T extends { data: { title: string; date?: Date } }>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    const da = a.data.date?.getTime();
    const db = b.data.date?.getTime();
    if (da !== undefined && db !== undefined) return db - da;
    if (da !== undefined) return -1;
    if (db !== undefined) return 1;
    return a.data.title.localeCompare(b.data.title, "ja");
  });
}

/** 下書き（draft: true）を除き、date の新しい順に並べる。 */
export function publishedArticles<T extends { data: { date: Date; draft: boolean } }>(items: T[]): T[] {
  return items
    .filter((i) => !i.data.draft)
    .sort((a, b) => b.data.date.getTime() - a.data.date.getTime());
}
