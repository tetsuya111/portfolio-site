import { describe, expect, it } from "vitest";
import { parseMarkdown, stringifyMarkdown } from "../src/lib/markdown-file";
import { ContentValidationError } from "../src/lib/errors";

describe("parseMarkdown", () => {
  it("splits frontmatter and body", () => {
    expect(parseMarkdown("---\ntitle: a\n---\n本文")).toEqual({ data: { title: "a" }, body: "本文" });
  });

  it("handles CRLF line endings", () => {
    expect(parseMarkdown("---\r\ntitle: a\r\n---\r\n本文\r\n")).toEqual({
      data: { title: "a" },
      body: "本文\r\n",
    });
  });

  it("throws without frontmatter", () => {
    expect(() => parseMarkdown("# just markdown")).toThrow(ContentValidationError);
  });

  it("throws when frontmatter is not a mapping", () => {
    expect(() => parseMarkdown("---\n- a\n---\nbody")).toThrow(ContentValidationError);
  });

  it("throws on broken yaml", () => {
    expect(() => parseMarkdown("---\ntitle: [unclosed\n---\nbody")).toThrow(ContentValidationError);
  });
});

describe("stringifyMarkdown", () => {
  it("round-trips through parseMarkdown", () => {
    const data = { title: 'He said "hi": ok', tags: ["Astro", "AWS"], url: "https://example.com" };
    const body = "## 概要\n\n本文\n";
    expect(parseMarkdown(stringifyMarkdown(data, body))).toEqual({ data, body });
  });
});
