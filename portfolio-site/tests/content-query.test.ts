import { describe, expect, it } from "vitest";
import { formatDisplayDate, publishedArticles, sortPortfolios } from "../src/lib/content-query";

describe("formatDisplayDate", () => {
  it("shows the authored calendar day regardless of the host timezone", () => {
    // frontmatter の `date: 2026-11-13` は UTC の 0 時として読み込まれる
    expect(formatDisplayDate(new Date("2026-11-13"))).toBe("2026/11/13");
    expect(formatDisplayDate(new Date("2026-01-01T00:00:00Z"))).toBe("2026/01/01");
  });
});

const p = (title: string, date?: string) => ({ data: { title, date: date ? new Date(date) : undefined } });
const a = (id: string, date: string, draft = false) => ({ id, data: { date: new Date(date), draft } });

describe("sortPortfolios", () => {
  it("orders by date desc, undated last by title", () => {
    const sorted = sortPortfolios([p("b"), p("old", "2025-01-01"), p("a"), p("new", "2026-01-01")]);
    expect(sorted.map((x) => x.data.title)).toEqual(["new", "old", "a", "b"]);
  });

  it("does not mutate the input", () => {
    const input = [p("b"), p("a")];
    sortPortfolios(input);
    expect(input.map((x) => x.data.title)).toEqual(["b", "a"]);
  });
});

describe("publishedArticles", () => {
  it("drops drafts and orders by date desc", () => {
    const r = publishedArticles([a("x", "2025-01-01"), a("d", "2027-01-01", true), a("y", "2026-01-01")]);
    expect(r.map((x) => x.id)).toEqual(["y", "x"]);
  });
});
