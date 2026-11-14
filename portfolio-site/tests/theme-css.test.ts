// src/styles/global.css のテーマ定義を検証する。
// axe はビルドした1テーマしか検査しないため、全テーマのコントラスト比はここで計算する。
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { DEFAULT_THEME, THEMES } from "../src/lib/theme";

const css = readFileSync(join(import.meta.dirname, "..", "src", "styles", "global.css"), "utf8").replace(
  /\/\*[\s\S]*?\*\//g,
  "",
);

const TOKENS = [
  "base",
  "surface",
  "fg",
  "muted",
  "line",
  "accent",
  "on-accent",
  "accent-soft",
  "on-accent-soft",
  "link",
  "focus",
  "hero-from",
  "hero-to",
  "font-body",
  "font-heading",
  "font-eyebrow",
  "radius",
];

/** セレクタ（例: `[data-theme="campus"]`）を含むルールの宣言を { 変数名: 値 } で返す */
function declarations(selectorPart: string): Record<string, string> {
  const result: Record<string, string> = {};
  for (const m of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    // 直前の @import などの文（; 区切り）を除いたものがセレクタ
    const selector = (m[1] ?? "").split(";").pop() ?? "";
    if (!selector.split(",").some((s) => s.trim() === selectorPart)) continue;
    for (const d of (m[2] ?? "").matchAll(/--theme-([\w-]+)\s*:\s*([^;]+);/g)) {
      result[d[1] as string] = (d[2] as string).trim();
    }
  }
  return result;
}

function luminance(hex: string): number {
  const m = /^#([0-9a-f]{6})$/i.exec(hex);
  if (!m) throw new Error(`#rrggbb 形式ではありません: ${hex}`);
  const [r, g, b] = [0, 2, 4].map((i) => {
    const c = parseInt((m[1] as string).slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (l1 + 0.05) / (l2 + 0.05);
}

const TEXT_PAIRS: [string, string][] = [
  ["fg", "base"],
  ["fg", "surface"],
  ["muted", "base"],
  ["muted", "surface"],
  ["link", "base"],
  ["link", "surface"],
  ["on-accent", "accent"],
  ["on-accent-soft", "accent-soft"],
  ["fg", "hero-from"],
  ["fg", "hero-to"],
  ["muted", "hero-from"],
  ["muted", "hero-to"],
  // 冒頭のパネルの小見出し（Hello・Profile）
  ["link", "hero-from"],
  ["link", "hero-to"],
];
// フォーカス枠など文字以外の要素は 3:1（WCAG 2.1 1.4.11）
const NON_TEXT_PAIRS: [string, string][] = [
  ["focus", "base"],
  ["focus", "surface"],
];

it("contrast() matches known values", () => {
  expect(contrast("#000000", "#ffffff")).toBeCloseTo(21, 5);
  expect(contrast("#777777", "#ffffff")).toBeCloseTo(4.48, 1);
});

describe.each(THEMES)("theme %s", (theme) => {
  const vars = declarations(`[data-theme="${theme}"]`);

  it("defines every token", () => {
    expect(Object.keys(vars).sort()).toEqual([...TOKENS].sort());
  });

  it.each(TEXT_PAIRS)("%s on %s has contrast >= 4.5", (fg, bg) => {
    expect(contrast(vars[fg] as string, vars[bg] as string)).toBeGreaterThanOrEqual(4.5);
  });

  it.each(NON_TEXT_PAIRS)("%s on %s has contrast >= 3", (fg, bg) => {
    expect(contrast(vars[fg] as string, vars[bg] as string)).toBeGreaterThanOrEqual(3);
  });
});

it("gives :root the default theme's values so pages without data-theme still render", () => {
  expect(declarations(":root")).toEqual(declarations(`[data-theme="${DEFAULT_THEME}"]`));
});
