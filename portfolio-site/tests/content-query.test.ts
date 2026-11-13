import { describe, expect, it } from "vitest";
import { publishedArticles, sortPortfolios } from "../src/lib/content-query";

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
