// astro build 後の dist/ を検証する（npm run test:build で実行）
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { loadEnv } from "vite";
import { describe, expect, it } from "vitest";
import { parseMarkdown } from "../src/lib/markdown-file";
import { resolveTheme } from "../src/lib/theme";
import { siteConfig } from "../src/site.config";

const dist = join(import.meta.dirname, "..", "dist");
const html = (p: string) => readFileSync(join(dist, p, "index.html"), "utf8");

describe("build output", () => {
  it("has dist/", () => {
    expect(existsSync(dist)).toBe(true);
  });

  it("shows portfolio tiles with title, tags and url button on the top page", () => {
    const top = html(".");
    expect(top).toContain("このポートフォリオサイト");
    expect(top).toContain("Astro");
    expect(top).toMatch(/href="\/"[^>]*target="_blank"|target="_blank"[^>]*href="\/"/);
    expect(top).toContain('href="/portfolios/sample-portfolio-site/"');
  });

  it("lists portfolios as tiles on the portfolio index page", () => {
    const list = html("portfolios");
    expect(list).toContain("このポートフォリオサイト");
    expect(list).toContain('href="/portfolios/sample-portfolio-site/"');
    expect(list).toMatch(/target="_blank"/);
    expect(list).toMatch(/<h1[^>]*>ポートフォリオ<\/h1>/);
    expect(list).toContain("<title>ポートフォリオ | Portfolio</title>");
  });

  it("links to the portfolio index from the header", () => {
    expect(html(".")).toMatch(/<a href="\/portfolios\/"[^>]*>\s*ポートフォリオ\s*<\/a>/);
  });

  it("links back to the portfolio index from the detail page", () => {
    expect(html("portfolios/sample-portfolio-site")).toMatch(/<a href="\/portfolios\/"[^>]*>← ポートフォリオ一覧<\/a>/);
  });

  it("renders the portfolio detail body", () => {
    expect(html("portfolios/sample-portfolio-site")).toMatch(/<h2[^>]*>概要<\/h2>/);
  });

  it("renders the profile on the about page", () => {
    // 名前はプロフィールの差し替えで変わるため、profile.md の frontmatter から読む
    const profile = parseMarkdown(readFileSync(join(import.meta.dirname, "..", "src", "content", "profile", "profile.md"), "utf8"));
    const name = profile.data.name;
    expect(typeof name === "string" && name.length > 0).toBe(true);
    expect(html("about")).toContain(`>${String(name)}</h1>`);
  });

  it("lists published articles and excludes drafts", () => {
    expect(html("articles")).toContain("はじめての記事");
    expect(html("articles")).not.toContain("下書きの記事");
    expect(existsSync(join(dist, "articles", "hello-world", "index.html"))).toBe(true);
    expect(existsSync(join(dist, "articles", "draft-sample"))).toBe(false);
  });

  it("has the IT news list page for auto-generated articles, linked from the article list", () => {
    expect(html("it-news")).toMatch(/<h1[^>]*>IT ニュース<\/h1>/);
    expect(html("it-news")).toContain("<title>IT ニュース | Portfolio</title>");
    expect(html("articles")).toMatch(/<a href="\/it-news\/"/);
  });

  it("lists the IT news generator as a portfolio", () => {
    expect(html("portfolios")).toContain('href="/portfolios/it-news-auto-articles/"');
    expect(html("portfolios/it-news-auto-articles")).toContain("IT ニュース自動作成");
  });

  it("keeps the back link on hand-written article pages", () => {
    expect(html("articles/hello-world")).toMatch(/<a href="\/articles\/"[^>]*>← 記事一覧<\/a>/);
  });

  it("contains no admin pages", () => {
    expect(existsSync(join(dist, "admin"))).toBe(false);
  });

  it("applies the selected design theme to every page", () => {
    // ビルドと同じ規則で期待値を決める。PUBLIC_THEME は astro build と同じく環境変数と .env ファイルの両方から読む
    const env = loadEnv("production", join(import.meta.dirname, ".."), "PUBLIC_");
    const theme = resolveTheme(env.PUBLIC_THEME, siteConfig.theme);
    for (const p of [".", "about", "portfolios", "articles", "it-news"]) {
      expect(html(p)).toContain(`<html lang="ja" data-theme="${theme}"`);
    }
  });

  it("has an svg favicon linked from the pages", () => {
    expect(existsSync(join(dist, "favicon.svg"))).toBe(true);
    expect(html(".")).toMatch(/<link rel="icon" type="image\/svg\+xml" href="\/favicon.svg"/);
  });

  it("has a 404 page", () => {
    expect(existsSync(join(dist, "404.html"))).toBe(true);
  });
});
