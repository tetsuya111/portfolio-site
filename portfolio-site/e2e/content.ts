// テストの期待値を src/content/ の md から読み込む。
// コンテンツを書き換えてもテストを直さずに済むよう、表示内容はここから求める。
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { parseMarkdown } from "../src/lib/markdown-file";
import { articleSchema, portfolioSchema, profileSchema, serviceSchema, skillSchema } from "../src/lib/schemas";
import { formatDisplayDate, limitTags, publishedArticles, sortByOrder, sortPortfolios } from "../src/lib/content-query";
import { CONTENT_ROOT } from "./fixtures";

function load<T>(dir: string, parse: (data: unknown) => T): { id: string; data: T; body: string }[] {
  return readdirSync(join(CONTENT_ROOT, dir))
    .filter((f) => f.endsWith(".md"))
    .map((f) => {
      const { data, body } = parseMarkdown(readFileSync(join(CONTENT_ROOT, dir, f), "utf8"));
      return { id: f.replace(/\.md$/, "").toLowerCase(), data: parse(data), body };
    });
}

export function loadProfile() {
  const [profile] = load("profile", (d) => profileSchema.parse(d));
  if (!profile) throw new Error("profile.md がありません");
  return profile;
}

/** 表示順（新しい順）に並べたポートフォリオ */
export function loadPortfolios() {
  return sortPortfolios(load("portfolios", (d) => portfolioSchema.parse(d)));
}

/** 公開される記事（下書きを除き、新しい順） */
export function loadPublishedArticles() {
  return publishedArticles(load("articles", (d) => articleSchema.parse(d)));
}

/** 公開される IT 記事（新しい順）。md は定期実行で作るため、0件のこともある */
export function loadPublishedItArticles() {
  return publishedArticles(load("it-articles", (d) => articleSchema.parse(d)));
}

/** 表示順（order の昇順）に並べたサービス */
export function loadServices() {
  return sortByOrder(load("services", (d) => serviceSchema.parse(d)));
}

/** 表示順（order の昇順）に並べたスキル */
export function loadSkills() {
  return sortByOrder(load("skills", (d) => skillSchema.parse(d)));
}

/** 下書きの記事 */
export function loadDraftArticles() {
  return load("articles", (d) => articleSchema.parse(d)).filter((a) => a.data.draft);
}

export { formatDisplayDate, limitTags };

/** すべての公開ページの URL */
export function allPublicPaths(): string[] {
  return [
    "/",
    "/about/",
    "/portfolios/",
    ...loadPortfolios().map((p) => `/portfolios/${p.id}/`),
    "/articles/",
    ...loadPublishedArticles().map((a) => `/articles/${a.id}/`),
  ];
}
