// profile.md の本文（自己紹介・経歴・スキル・資格）の読み取りを確かめる
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { parseMarkdown } from "../src/lib/markdown-file";
import { parseProfileBody } from "../src/lib/profile-body";

const sample = [
  "## 自己紹介",
  "",
  "一段落目。",
  "続きの行。",
  "",
  "二段落目。",
  "",
  "## 経歴",
  "",
  "- 2022年〜2023年: インフラ構築（Bind による DNS、Zabbix 監視）",
  "- 2026年〜：営業支援ツール（ブラウザ拡張機能）の開発（Python・Go、AWS）",
  "- 2027年: 詳細なし",
  "",
  "## スキル",
  "",
  "- Python / Go",
  "- AWS / Linux（RHEL・Ubuntu）",
  "",
  "### 資格",
  "",
  "- CCNA / LPIC 101",
  "",
].join("\n");

describe("parseProfileBody", () => {
  it("reads the intro, career, skills and certifications", () => {
    expect(parseProfileBody(sample)).toEqual({
      // 段落内の改行は Markdown と同じく残す（HTML では空白として表示される）
      intro: ["一段落目。\n続きの行。", "二段落目。"],
      career: [
        { period: "2022年〜2023年", title: "インフラ構築", details: ["Bind による DNS", "Zabbix 監視"] },
        { period: "2026年〜", title: "営業支援ツール（ブラウザ拡張機能）の開発", details: ["Python・Go", "AWS"] },
        { period: "2027年", title: "詳細なし", details: [] },
      ],
      skills: [
        ["Python", "Go"],
        ["AWS", "Linux（RHEL・Ubuntu）"],
      ],
      certifications: [["CCNA", "LPIC 101"]],
    });
  });

  it("accepts CRLF line endings", () => {
    expect(parseProfileBody(sample.replaceAll("\n", "\r\n"))).toEqual(parseProfileBody(sample));
  });

  it("splits details only on 、 outside nested parentheses", () => {
    const body = "## 経歴\n\n- 2025年: 開発（React（Next.js、Remix）、TypeScript）\n";
    expect(parseProfileBody(body)?.career[0]?.details).toEqual(["React（Next.js、Remix）", "TypeScript"]);
    const half = "## 経歴\n\n- 2025年: 開発（React (Next.js、Remix)、TypeScript）\n";
    expect(parseProfileBody(half)?.career[0]?.details).toEqual(["React (Next.js、Remix)", "TypeScript"]);
  });

  it("allows sections to be missing", () => {
    expect(parseProfileBody("## スキル\n\n- Python\n")).toEqual({
      intro: [],
      career: [],
      skills: [["Python"]],
      certifications: [],
    });
  });

  it.each([
    ["an unknown ## heading", `${sample}\n## 趣味\n\n- 読書\n`],
    ["an unknown ### heading", sample.replace("### 資格", "### 受賞")],
    ["text before the first heading", `はじめに\n\n${sample}`],
    ["a career line without a period", sample.replace("- 2027年: 詳細なし", "- 詳細なし")],
    ["a non-list line in the career", sample.replace("- 2027年: 詳細なし", "補足の文")],
    ["a non-list line in the skills", sample.replace("- Python / Go", "Python / Go")],
    ["a link", sample.replace("一段落目。", "[GitHub](https://github.com/)")],
    ["emphasis", sample.replace("一段落目。", "**一段落目**")],
    ["inline code", sample.replace("- Python / Go", "- `Python` / Go")],
    ["html", sample.replace("二段落目。", "<b>二段落目</b>")],
    ["a nested list", sample.replace("- Python / Go", "- Python / Go\n  - Django")],
    ["an empty body", ""],
    ["only empty sections", "## 自己紹介\n\n## 経歴\n"],
    ["an empty section", "## 自己紹介\n\n本文。\n\n## 経歴\n\n## スキル\n\n- Python\n"],
    ["sections out of order", "## スキル\n\n- Python\n\n## 経歴\n\n- 2022年: 開発\n"],
    ["a short setext underline", sample.replace("二段落目。", "見出し\n=")],
    ["a short setext underline with -", sample.replace("二段落目。", "見出し\n--")],
    ["a bare url", sample.replace("二段落目。", "ブログ: https://example.com")],
    ["a www url", sample.replace("二段落目。", "www.example.com")],
    ["ascii quotes", sample.replace("二段落目。", 'Python "API"')],
    ["an apostrophe", sample.replace("二段落目。", "It's")],
    ["a double hyphen", sample.replace("二段落目。", "a -- b")],
    ["an ellipsis", sample.replace("二段落目。", "続く...")],
    ["an email address", sample.replace("二段落目。", "連絡: me@example.com")],
    ["a hard line break", sample.replace("一段落目。\n", "一段落目。  \n")],
    ["a nested ordered list marker", sample.replace("- Python / Go", "- 1. Python / Go")],
    ["a nested bullet marker", sample.replace("- Python / Go", "- - Python / Go")],
  ])("returns null for %s", (_, body) => {
    expect(parseProfileBody(body)).toBeNull();
  });

  it("reads the real profile.md", () => {
    const md = readFileSync(join(import.meta.dirname, "..", "src", "content", "profile", "profile.md"), "utf8");
    const parsed = parseProfileBody(parseMarkdown(md).body);
    expect(parsed).not.toBeNull();
    expect(parsed?.intro.length).toBeGreaterThan(0);
    expect(parsed?.career.length).toBeGreaterThan(0);
    for (const c of parsed?.career ?? []) expect(c.period).toMatch(/^\d{4}年/);
    expect(parsed?.skills.length).toBeGreaterThan(0);
  });
});
