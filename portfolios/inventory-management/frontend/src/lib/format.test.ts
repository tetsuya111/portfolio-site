import { describe, expect, it } from "vitest";

import { formatDateTime, formatNumber, movementTypeLabel, ROLE_LABEL } from "./format";

describe("format", () => {
  it("formatNumber adds separators", () => {
    expect(formatNumber(0)).toBe("0");
    expect(formatNumber(1234567)).toBe("1,234,567");
  });

  it("ROLE_LABEL shows visitor as 閲覧者", () => {
    expect(ROLE_LABEL.visitor).toBe("閲覧者");
  });

  it("movementTypeLabel", () => {
    expect(movementTypeLabel("in")).toBe("入庫");
    expect(movementTypeLabel("out")).toBe("出庫");
  });

  it("formatDateTime renders local date and time", () => {
    const text = formatDateTime("2026-01-10T03:04:00+00:00");
    expect(text).toMatch(/2026\/0?1\/\d{1,2} \d{1,2}:\d{2}/);
  });

  it("formatDateTime returns dash for invalid input", () => {
    expect(formatDateTime("not-a-date")).toBe("—");
  });
});
