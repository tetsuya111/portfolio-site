// 公開ページのコンポーネントに、特定の色を直接指定するクラス（text-slate-700 など）がないことを確かめる。
// 色はテーマのトークン（text-fg・bg-accent など。src/styles/global.css）で指定する。
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { expect, it } from "vitest";

const src = join(import.meta.dirname, "..", "src");
const DIRS = ["pages", "components", "layouts"];

const PALETTE =
  "slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose";
const UTILITIES =
  "text|bg|border|ring|ring-offset|outline|from|via|to|fill|stroke|decoration|divide|shadow|accent|caret|placeholder";
const HARDCODED = new RegExp(
  [
    // パレットの色: text-slate-700・border-x-white など
    `\\b(?:[\\w-]+:)*(?:${UTILITIES})(?:-[trblxyse])?-(?:(?:${PALETTE})-\\d{2,3}|white|black)\\b`,
    // 任意値の色: bg-[#fff]・text-[rgb(0,0,0)] など
    `\\b(?:[\\w-]+:)*(?:${UTILITIES})(?:-[trblxyse])?-\\[(?:#|rgb|hsl|oklch|oklab|color)[^\\]]*\\]`,
    // typography プラグインの色: prose-slate など（色は prose-themed で指定する）
    `\\bprose-(?:${PALETTE})\\b`,
  ].join("|"),
  "g",
);

function astroFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true, recursive: true })
    .filter((e) => e.isFile() && e.name.endsWith(".astro"))
    .map((e) => join(e.parentPath, e.name));
}

it("the pattern detects hardcoded colors", () => {
  const sample =
    "text-slate-700 hover:bg-sky-50 border-white bg-[#fff] text-[rgb(0,0,0)] ring-offset-white placeholder-gray-400 prose-slate " +
    "text-fg bg-accent prose-themed bg-[var(--theme-base)] border-t-accent";
  expect(sample.match(HARDCODED)).toEqual([
    "text-slate-700",
    "hover:bg-sky-50",
    "border-white",
    "bg-[#fff]",
    "text-[rgb(0,0,0)]",
    "ring-offset-white",
    "placeholder-gray-400",
    "prose-slate",
  ]);
});

it("public page components use theme tokens instead of hardcoded colors", () => {
  const found = DIRS.flatMap((d) => astroFiles(join(src, d))).flatMap((file) =>
    (readFileSync(file, "utf8").match(HARDCODED) ?? []).map((m) => `${relative(src, file)}: ${m}`),
  );
  expect(found).toEqual([]);
});
