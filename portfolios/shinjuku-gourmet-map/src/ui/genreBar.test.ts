import { beforeEach, describe, expect, test, vi } from "vitest";
import type { Genre } from "../config/parseMapConfig";
import { createGenreBar } from "./genreBar";

const genres: Genre[] = [
  { id: "ramen", label: "ラーメン", query: "q", icon: "🍜" },
  { id: "cafe", label: "カフェ", query: "q" },
  { id: "izakaya", label: "居酒屋", query: "q" },
];

let container: HTMLElement;
beforeEach(() => {
  container = document.createElement("nav");
});

const buttons = () => [...container.querySelectorAll("button")];

describe("createGenreBar", () => {
  test("定義順に type=button のボタンを描画する", () => {
    createGenreBar(container, genres, () => {});
    expect(buttons().map((b) => b.textContent)).toEqual(["🍜ラーメン", "カフェ", "居酒屋"]);
    expect(buttons().every((b) => b.type === "button")).toBe(true);
  });

  test("アイコンは読み上げ対象から外す", () => {
    createGenreBar(container, genres, () => {});
    expect(buttons()[0].querySelector(".genre-button__icon")?.getAttribute("aria-hidden")).toBe("true");
  });

  test("クリックでジャンルを通知する", () => {
    const onSelect = vi.fn();
    createGenreBar(container, genres, onSelect);
    buttons()[1].click();
    expect(onSelect).toHaveBeenCalledWith(genres[1]);
  });

  test("setActive で選択中のボタンだけ aria-pressed と選択クラスが付く", () => {
    const bar = createGenreBar(container, genres, () => {});
    expect(buttons().map((b) => b.getAttribute("aria-pressed"))).toEqual(["false", "false", "false"]);
    bar.setActive("cafe");
    expect(buttons().map((b) => b.getAttribute("aria-pressed"))).toEqual(["false", "true", "false"]);
    expect(buttons()[1].classList.contains("genre-button--active")).toBe(true);
    bar.setActive("izakaya");
    expect(buttons()[1].classList.contains("genre-button--active")).toBe(false);
    expect(buttons()[2].getAttribute("aria-pressed")).toBe("true");
  });

  test("再描画しても前のボタンが残らない", () => {
    createGenreBar(container, genres, () => {});
    createGenreBar(container, genres.slice(0, 1), () => {});
    expect(buttons()).toHaveLength(1);
  });

  test("setDisabled でボタンを押せなくする", () => {
    const bar = createGenreBar(container, genres, () => {});
    bar.setDisabled(true);
    expect(buttons().every((b) => b.disabled)).toBe(true);
    bar.setDisabled(false);
    expect(buttons().some((b) => b.disabled)).toBe(false);
  });
});
