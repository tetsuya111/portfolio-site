import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AGE_KEY, AgeGate } from "./AgeGate";

function renderGate() {
  return render(
    <AgeGate>
      <p>本文</p>
    </AgeGate>,
  );
}

describe("AgeGate", () => {
  it("未確認なら内容を表示しない", () => {
    renderGate();
    expect(screen.getByRole("heading", { name: "年齢確認" })).toBeInTheDocument();
    expect(screen.queryByText("本文")).not.toBeInTheDocument();
  });

  it("18歳以上と答えると内容を表示し、回答を保存する", async () => {
    renderGate();
    await userEvent.click(screen.getByRole("button", { name: /はい/ }));
    expect(screen.getByText("本文")).toBeInTheDocument();
    expect(localStorage.getItem(AGE_KEY)).toBe("yes");
  });

  it("保存済みなら確認を省略する", () => {
    localStorage.setItem(AGE_KEY, "yes");
    renderGate();
    expect(screen.getByText("本文")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "年齢確認" })).not.toBeInTheDocument();
  });

  it("18歳未満と答えると内容を表示せず案内を出す", async () => {
    renderGate();
    await userEvent.click(screen.getByRole("button", { name: /いいえ/ }));
    expect(screen.getByRole("alert")).toHaveTextContent("18歳未満の方はご利用いただけません");
    expect(screen.queryByText("本文")).not.toBeInTheDocument();
    expect(localStorage.getItem(AGE_KEY)).toBeNull();
  });
});
