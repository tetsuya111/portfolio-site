import { describe, expect, it } from "vitest";
import { formatDisplayDate, limitTags, publishedArticles, sortByOrder, sortPortfolios } from "../src/lib/content-query";

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

describe("sortByOrder", () => {
  it("orders by order asc, then by title or name", () => {
    const items = [
      { data: { order: 2, title: "い" } },
      { data: { order: 1, name: "う" } },
      { data: { order: 2, title: "あ" } },
    ];
    expect(sortByOrder(items).map((i) => ("title" in i.data ? i.data.title : i.data.name))).toEqual(["う", "あ", "い"]);
  });

  it("does not mutate the input", () => {
    const items = [{ data: { order: 2, title: "b" } }, { data: { order: 1, title: "a" } }];
    sortByOrder(items);
    expect(items[0]?.data.title).toBe("b");
  });
});

describe("limitTags", () => {
  const tags = (n: number) => Array.from({ length: n }, (_, i) => `t${i}`);

  it("shows the first 5 and counts the rest", () => {
    expect(limitTags(tags(7))).toEqual({ shown: tags(5), rest: 2 });
  });

  it("shows all when there are exactly 5", () => {
    expect(limitTags(tags(5))).toEqual({ shown: tags(5), rest: 0 });
  });

  it("handles no tags and a custom max", () => {
    expect(limitTags([])).toEqual({ shown: [], rest: 0 });
    expect(limitTags(tags(3), 2)).toEqual({ shown: tags(2), rest: 1 });
  });
});
