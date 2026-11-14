// 公開ページのコンポーネントに、特定の色を直接指定するクラス（text-slate-700 など）がないことを確かめる。
// 色はテーマのトークン（text-fg・bg-accent など。src/styles/global.css）で指定する。
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { expect, it } from "vitest";

const src = join(import.meta.dirname, "..", "src");
const DIRS = ["pages", "components", "layouts"];

const PALETTE =
  "slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose";
const UTILITIES = "text|bg|border|ring|outline|from|via|to|fill|stroke|decoration|divide|shadow|accent|caret";
const HARDCODED = new RegExp(`\\b(?:[\\w-]+:)*(?:${UTILITIES})(?:-[trblxy])?-(?:(?:${PALETTE})-\\d{2,3}|white|black)\\b`, "g");

function astroFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true, recursive: true })
    .filter((e) => e.isFile() && e.name.endsWith(".astro"))
    .map((e) => join(e.parentPath, e.name));
}

it("the pattern detects hardcoded colors", () => {
  expect("text-slate-700 hover:bg-sky-50 border-white text-fg bg-accent".match(HARDCODED)).toEqual([
    "text-slate-700",
    "hover:bg-sky-50",
    "border-white",
  ]);
});

it("public page components use theme tokens instead of hardcoded colors", () => {
  const found = DIRS.flatMap((d) => astroFiles(join(src, d))).flatMap((file) =>
    (readFileSync(file, "utf8").match(HARDCODED) ?? []).map((m) => `${relative(src, file)}: ${m}`),
  );
  expect(found).toEqual([]);
});
