// テストの期待値を src/content/ の md から読み込む。
// コンテンツを書き換えてもテストを直さずに済むよう、表示内容はここから求める。
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { parseMarkdown } from "../src/lib/markdown-file";
import { articleSchema, portfolioSchema, profileSchema } from "../src/lib/schemas";
import { formatDisplayDate, publishedArticles, sortPortfolios } from "../src/lib/content-query";
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

/** 下書きの記事 */
export function loadDraftArticles() {
  return load("articles", (d) => articleSchema.parse(d)).filter((a) => a.data.draft);
}

export { formatDisplayDate };

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
