// astro build 後の dist/ を検証する（npm run test:build で実行）
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { loadEnv } from "vite";
import { describe, expect, it } from "vitest";
import { parseMarkdown } from "../src/lib/markdown-file";
import { sortByOrder, sortPortfolios } from "../src/lib/content-query";
import { audienceSchema, portfolioSchema } from "../src/lib/schemas";
import { resolveConsultation } from "../src/lib/consultation";
import { resolveTheme } from "../src/lib/theme";
import { siteConfig } from "../src/site.config";

const dist = join(import.meta.dirname, "..", "dist");
const html = (p: string) => readFileSync(join(dist, p, "index.html"), "utf8");

describe("build output", () => {
  it("has dist/", () => {
    expect(existsSync(dist)).toBe(true);
  });

  it("shows the consultation buttons, services and skills on the top page", () => {
    const top = html(".");
    expect(top).toMatch(/<h2[^>]*>ご相談はこちら<\/h2>/);
    expect(top).toMatch(/<h2[^>]*>サービス<\/h2>/);
    expect(top).toMatch(/<h2[^>]*>スキル<\/h2>/);
    expect(top).toContain("※このサービスは一例です。相談していただければなんでも対応します。");
    // フォームは宛先が有効なときだけ出す。ビルドと同じく環境変数と .env ファイルの両方から読む
    const env = loadEnv("production", join(import.meta.dirname, ".."), "PUBLIC_");
    const c = resolveConsultation(
      { contactEmail: env.PUBLIC_CONTACT_EMAIL, taskBoxUrl: env.PUBLIC_TASK_BOX_URL },
      siteConfig,
    );
    expect(top.includes("<dialog")).toBe(c.contactEmail !== null);
    // Astro は属性値の & を &amp; にして出力する
    if (c.taskBox) expect(top).toContain(`href="${c.taskBox.href.replaceAll("&", "&amp;")}"`);
  });

  it("shows the audiences as tiles right after the services on the top page", () => {
    const dir = join(import.meta.dirname, "..", "src", "content", "audiences");
    const titles = sortByOrder(
      readdirSync(dir)
        .filter((f) => f.endsWith(".md"))
        .map((f) => ({ data: audienceSchema.parse(parseMarkdown(readFileSync(join(dir, f), "utf8")).data) })),
    ).map((a) => a.data.title);
    expect(titles.length).toBeGreaterThan(0);
    const top = html(".");
    const heading = top.search(/<h2[^>]*>こんな方とお話ししたい<\/h2>/);
    expect(heading).toBeGreaterThan(top.search(/<h2[^>]*>サービス<\/h2>/));
    expect(heading).toBeLessThan(top.search(/<h2[^>]*>ポートフォリオ<\/h2>/));
    // タイトルが order の順に、見出しの後に並ぶ
    let pos = heading;
    for (const t of titles) {
      const next = top.indexOf(`>${t}</h3>`, pos);
      expect(next, t).toBeGreaterThan(pos);
      pos = next;
    }
  });

  it("shows portfolio tiles with title, tags and url button on the top page", () => {
    // トップページは新しい順に6件だけを出すため、もっとも新しいポートフォリオで確かめる
    const dir = join(import.meta.dirname, "..", "src", "content", "portfolios");
    const [newest] = sortPortfolios(
      readdirSync(dir)
        .filter((f) => f.endsWith(".md"))
        .map((f) => ({
          id: f.replace(/\.md$/, "").toLowerCase(),
          data: portfolioSchema.parse(parseMarkdown(readFileSync(join(dir, f), "utf8")).data),
        })),
    );
    if (!newest) throw new Error("ポートフォリオの md がありません");
    const top = html(".");
    expect(top).toContain(newest.data.title);
    expect(top).toContain(`href="/portfolios/${newest.id}/"`);
    if (newest.data.tags[0]) expect(top).toContain(newest.data.tags[0]);
    if (newest.data.url) {
      // URL ボタン（別タブで開く）が出ている
      expect(top).toMatch(
        new RegExp(
          `<a href="${newest.data.url.replaceAll("&", "&amp;").replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"[^>]*target="_blank"[^>]*>\\s*ポートフォリオのURL ↗`,
        ),
      );
    }
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

  it("has the security news list page for auto-generated articles, linked from the article list", () => {
    expect(html("security-news")).toMatch(/<h1[^>]*>セキュリティニュース<\/h1>/);
    expect(html("security-news")).toContain("<title>セキュリティニュース | Portfolio</title>");
    expect(html("articles")).toMatch(/<a href="\/security-news\/"/);
  });

  it("lists the security news generator as a portfolio", () => {
    expect(html("portfolios")).toContain('href="/portfolios/security-news-auto-articles/"');
    expect(html("portfolios/security-news-auto-articles")).toContain("セキュリティニュース自動作成");
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
    for (const p of [".", "about", "portfolios", "articles", "it-news", "security-news"]) {
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
