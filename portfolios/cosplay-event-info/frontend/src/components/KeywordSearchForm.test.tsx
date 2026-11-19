import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { KeywordSearchForm } from "./KeywordSearchForm";

describe("KeywordSearchForm", () => {
  it("初期値を表示し、入力したキーワードを onSearch に渡す", async () => {
    const onSearch = vi.fn();
    const user = userEvent.setup();
    render(<KeywordSearchForm initial="花子" placeholder="名前" onSearch={onSearch} />);

    const input = screen.getByLabelText("キーワード");
    expect(input).toHaveValue("花子");
    await user.clear(input);
    await user.type(input, "太郎");
    await user.click(screen.getByRole("button", { name: "検索" }));

    expect(onSearch).toHaveBeenCalledWith("太郎");
  });
});
