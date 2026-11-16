import { describe, expect, it } from "vitest";

import { lowStockItems, topStocked } from "./dashboard";
import type { SummaryItem } from "./types";

const item = (sku: string, stock: number, is_low = false): SummaryItem => ({
  product_id: stock,
  sku,
  name: sku,
  unit: "個",
  stock,
  reorder_point: 0,
  is_low,
});

describe("dashboard", () => {
  it("topStocked returns top n by stock", () => {
    const items = Array.from({ length: 12 }, (_, i) => item(`P${i}`, i));
    const top = topStocked(items);
    expect(top).toHaveLength(10);
    expect(top[0].sku).toBe("P11");
    expect(topStocked(items, 3).map((i) => i.sku)).toEqual(["P11", "P10", "P9"]);
  });

  it("lowStockItems filters is_low and sorts by stock", () => {
    const items = [item("A", 5, true), item("B", 50), item("C", 1, true)];
    expect(lowStockItems(items).map((i) => i.sku)).toEqual(["C", "A"]);
  });
});
