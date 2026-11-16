import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";

import { ProductForm } from "./ProductForm";

describe("ProductForm", () => {
  it("requires sku and name", async () => {
    const onSubmit = vi.fn();
    render(<ProductForm onSubmit={onSubmit} submitLabel="登録" />);
    await userEvent.click(screen.getByRole("button", { name: "登録" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByLabelText("商品コード")).toBeInvalid();
    expect(screen.getByLabelText("商品名")).toBeInvalid();
  });

  it("submits numbers or null", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ProductForm onSubmit={onSubmit} submitLabel="登録" />);
    await userEvent.type(screen.getByLabelText("商品コード"), " A-001 ");
    await userEvent.type(screen.getByLabelText("商品名"), "ボールペン");
    await userEvent.type(screen.getByLabelText("発注点"), "{selectall}12");
    await userEvent.click(screen.getByRole("button", { name: "登録" }));
    expect(onSubmit).toHaveBeenCalledWith({
      sku: "A-001",
      name: "ボールペン",
      category: null,
      unit: "個",
      unit_price: null,
      reorder_point: 12,
      description: null,
    });
  });

  it("fills initial values for editing", () => {
    render(
      <ProductForm
        initial={{
          sku: "B-1",
          name: "ノート",
          category: "文具",
          unit: "冊",
          unit_price: 180,
          reorder_point: 5,
          description: "A5",
        }}
        onSubmit={vi.fn()}
        submitLabel="更新"
      />,
    );
    expect(screen.getByLabelText("商品コード")).toHaveValue("B-1");
    expect(screen.getByLabelText("単価（円）")).toHaveValue(180);
    expect(screen.getByLabelText("説明")).toHaveValue("A5");
  });

  it("shows api error", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new ApiError(409, "この商品コードは既に使われています"));
    render(<ProductForm onSubmit={onSubmit} submitLabel="登録" />);
    await userEvent.type(screen.getByLabelText("商品コード"), "A-001");
    await userEvent.type(screen.getByLabelText("商品名"), "ボールペン");
    await userEvent.click(screen.getByRole("button", { name: "登録" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("この商品コードは既に使われています");
  });
});
