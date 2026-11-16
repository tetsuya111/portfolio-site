import { describe, expect, it } from "vitest";

import { sortSummaryItems } from "./sort";
import type { SummaryItem } from "./types";

const item = (sku: string, stock: number): SummaryItem => ({
  product_id: stock,
  sku,
  name: sku,
  unit: "個",
  stock,
  reorder_point: 0,
  is_low: false,
});

describe("sortSummaryItems", () => {
  const items = [item("B", 5), item("A", 10), item("C", 1), item("D", 5)];

  it("sorts by stock ascending, ties by sku", () => {
    expect(sortSummaryItems(items, "asc").map((i) => i.sku)).toEqual(["C", "B", "D", "A"]);
  });

  it("sorts by stock descending, ties by sku", () => {
    expect(sortSummaryItems(items, "desc").map((i) => i.sku)).toEqual(["A", "B", "D", "C"]);
  });

  it("does not mutate the input", () => {
    sortSummaryItems(items, "asc");
    expect(items.map((i) => i.sku)).toEqual(["B", "A", "C", "D"]);
  });
});
