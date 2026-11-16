import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BarChart } from "./BarChart";

describe("BarChart", () => {
  it("renders bars proportional to max", () => {
    render(
      <BarChart
        data={[
          { label: "A", value: 200 },
          { label: "B", value: 50 },
          { label: "C", value: 0 },
        ]}
        emptyText="データがありません。"
      />,
    );
    const bars = screen.getAllByTestId("bar-fill");
    expect(bars.map((b) => b.style.width)).toEqual(["100%", "25%", "0%"]);
    expect(screen.getByText("200")).toBeInTheDocument();
    expect(screen.getByRole("list")).toHaveAccessibleName(/在庫数/);
  });

  it("shows empty text", () => {
    render(<BarChart data={[]} emptyText="データがありません。" />);
    expect(screen.getByText("データがありません。")).toBeInTheDocument();
  });

  it("does not divide by zero when all values are 0", () => {
    render(<BarChart data={[{ label: "A", value: 0 }]} emptyText="なし" />);
    expect(screen.getByTestId("bar-fill").style.width).toBe("0%");
  });
});
