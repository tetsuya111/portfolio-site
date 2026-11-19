import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { EventSearchForm } from "./EventSearchForm";

describe("EventSearchForm", () => {
  it("入力した条件を onSearch に渡す", async () => {
    const onSearch = vi.fn();
    const user = userEvent.setup();
    render(<EventSearchForm initial={{}} onSearch={onSearch} />);

    await user.type(screen.getByLabelText("キーワード"), "撮影会");
    await user.type(screen.getByLabelText("開始日"), "2026-12-01");
    await user.type(screen.getByLabelText("終了日"), "2026-12-31");
    await user.selectOptions(screen.getByLabelText("都道府県"), "大阪府");
    await user.click(screen.getByRole("button", { name: "検索" }));

    expect(onSearch).toHaveBeenCalledWith({
      q: "撮影会",
      from: "2026-12-01",
      to: "2026-12-31",
      prefecture: "大阪府",
    });
  });

  it("初期値を表示し、クリアで空の条件を渡す", async () => {
    const onSearch = vi.fn();
    const user = userEvent.setup();
    render(<EventSearchForm initial={{ q: "祭り", prefecture: "東京都" }} onSearch={onSearch} />);

    expect(screen.getByLabelText("キーワード")).toHaveValue("祭り");
    expect(screen.getByLabelText("都道府県")).toHaveValue("東京都");

    await user.click(screen.getByRole("button", { name: "クリア" }));

    expect(onSearch).toHaveBeenCalledWith({ q: "", from: "", to: "", prefecture: "" });
    expect(screen.getByLabelText("キーワード")).toHaveValue("");
  });
});
