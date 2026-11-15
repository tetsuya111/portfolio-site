// src/content/ の md（サービス・スキル・ポートフォリオ）がスキーマを満たし、トップページに必要な項目を持つことを確かめる
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { parseMarkdown } from "../src/lib/markdown-file";
import { portfolioSchema, serviceSchema, skillSchema } from "../src/lib/schemas";

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

  it("has valid portfolios", () => {
    // description は任意（ポートフォリオ追加コマンドでは書かれない）。あればタイルに出す
    for (const i of frontmatters("portfolios")) expect(portfolioSchema.safeParse(i.data).success, i.file).toBe(true);
  });
});
