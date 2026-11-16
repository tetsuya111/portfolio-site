import { beforeEach, describe, expect, test } from "vitest";
import type { Genre } from "../config/parseMapConfig";
import { createStatusView } from "./statusView";

const ramen: Genre = { id: "ramen", label: "ラーメン", query: "q" };
let el: HTMLElement;
beforeEach(() => {
  el = document.createElement("div");
});

describe("createStatusView", () => {
  test("変化を読み上げられるよう role=status を付ける", () => {
    createStatusView(el);
    expect(el.getAttribute("role")).toBe("status");
    expect(el.getAttribute("aria-live")).toBe("polite");
  });

  test("読み込み中を表示する", () => {
    const view = createStatusView(el);
    view.loading(ramen);
    expect(el.textContent).toBe("ラーメンのお店を探しています…");
    expect(el.dataset.state).toBe("loading");
  });

  test("ジャンル名と件数を表示する", () => {
    const view = createStatusView(el);
    view.result(ramen, 12);
    expect(el.textContent).toBe("ラーメン: 12件");
    expect(el.dataset.state).toBe("result");
  });

  test("0件なら見つからなかったことを表示する", () => {
    const view = createStatusView(el);
    view.result(ramen, 0);
    expect(el.textContent).toBe("ラーメン: お店が見つかりませんでした");
    expect(el.dataset.state).toBe("empty");
  });

  test("エラーを表示する", () => {
    const view = createStatusView(el);
    view.error("検索に失敗しました");
    expect(el.textContent).toBe("検索に失敗しました");
    expect(el.dataset.state).toBe("error");
  });

  test("問題の一覧を箇条書きで表示する", () => {
    const view = createStatusView(el);
    view.error("設定に誤りがあります", ["a: x", "<b>: y"]);
    expect(el.querySelector("p")?.textContent).toBe("設定に誤りがあります");
    expect([...el.querySelectorAll("li")].map((li) => li.textContent)).toEqual(["a: x", "<b>: y"]);
    expect(el.querySelector("b")).toBeNull();
  });
});
