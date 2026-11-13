// astro build 後の dist/ を検証する（npm run test:build で実行）
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

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
    expect(top).toMatch(/href="https:\/\/example\.com\/"[^>]*target="_blank"|target="_blank"[^>]*href="https:\/\/example\.com\/"/);
    expect(top).toContain('href="/portfolios/sample-portfolio-site/"');
  });

  it("renders the portfolio detail body", () => {
    expect(html("portfolios/sample-portfolio-site")).toMatch(/<h2[^>]*>概要<\/h2>/);
  });

  it("renders the profile on the about page", () => {
    expect(html("about")).toContain("山田 太郎");
  });

  it("lists published articles and excludes drafts", () => {
    expect(html("articles")).toContain("はじめての記事");
    expect(html("articles")).not.toContain("下書きの記事");
    expect(existsSync(join(dist, "articles", "hello-world", "index.html"))).toBe(true);
    expect(existsSync(join(dist, "articles", "draft-sample"))).toBe(false);
  });

  it("contains no admin pages", () => {
    expect(existsSync(join(dist, "admin"))).toBe(false);
  });

  it("has a 404 page", () => {
    expect(existsSync(join(dist, "404.html"))).toBe(true);
  });
});
