// src/content/ の md（サービス・スキル・こんな方とお話ししたい・ポートフォリオ）がスキーマを満たし、トップページに必要な項目を持つことを確かめる
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { parseMarkdown } from "../src/lib/markdown-file";
import { audienceSchema, portfolioSchema, profileSchema, serviceSchema, skillSchema } from "../src/lib/schemas";
import { sortByOrder } from "../src/lib/content-query";

const root = join(import.meta.dirname, "..", "src", "content");

function frontmatters(dir: string): { file: string; data: unknown }[] {
  return readdirSync(join(root, dir))
    .filter((f) => f.endsWith(".md"))
    .map((f) => ({ file: f, data: parseMarkdown(readFileSync(join(root, dir, f), "utf8")).data }));
}

describe("content files", () => {
  it("has at least 6 valid services", () => {
    const items = frontmatters("services");
    expect(items.length).toBeGreaterThanOrEqual(6);
    for (const i of items) expect(serviceSchema.safeParse(i.data).success, i.file).toBe(true);
  });

  it("has at least 6 valid skills with examples and famous uses", () => {
    const items = frontmatters("skills");
    expect(items.length).toBeGreaterThanOrEqual(6);
    for (const i of items) {
      const r = skillSchema.safeParse(i.data);
      expect(r.success, i.file).toBe(true);
      expect(r.data?.examples.length, i.file).toBeGreaterThan(0);
      expect(r.data?.famous.length, i.file).toBeGreaterThan(0);
    }
  });

  it("has the audiences from the memo, in order", () => {
    const items = frontmatters("audiences").map((i) => {
      expect(audienceSchema.safeParse(i.data).success, i.file).toBe(true);
      return { data: audienceSchema.parse(i.data) };
    });
    expect(sortByOrder(items).map((i) => i.data.title)).toEqual([
      "会社に受注するのはハードルが高いと感じる方",
      "個人事業主でITツールを作成してほしい方",
      "要件の整理から開発まで丁寧にフォローしてほしい方",
      "IT開発の基盤を整えたい方",
    ]);
  });

  it("has the self-introduction from the memo and keeps the other profile sections", () => {
    const { data, body } = parseMarkdown(readFileSync(join(root, "profile", "profile.md"), "utf8"));
    expect(profileSchema.safeParse(data).success).toBe(true);
    // 「## 自己紹介」の見出しから次の「## 」見出しまで（改行は CRLF・LF のどちらでもよい）
    const intro = /^## 自己紹介\r?\n([\s\S]*?)(?=^## )/m.exec(body)?.[1];
    expect(intro).toContain("システム開発からクラウド構築まで");
    expect(intro).toContain("直接やりとりするためにこのサイトを作成しました");
    for (const h of ["## 経歴", "## スキル", "### 資格"]) expect(body).toMatch(new RegExp(`^${h}\\r?$`, "m"));
  });

  it("has valid portfolios", () => {
    // description は任意（ポートフォリオ追加コマンドでは書かれない）。あればタイルに出す
    for (const i of frontmatters("portfolios")) expect(portfolioSchema.safeParse(i.data).success, i.file).toBe(true);
  });
});
