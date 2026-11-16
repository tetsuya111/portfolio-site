import type { Genre } from "../config/parseMapConfig";

export interface GenreBar {
  /** 選択中のジャンルを切り替える（見た目と aria-pressed） */
  setActive(genreId: string): void;
}

/** 設定ファイルのジャンルを定義順にボタンとして描画する */
export function createGenreBar(
  container: HTMLElement,
  genres: Genre[],
  onSelect: (genre: Genre) => void,
): GenreBar {
  const buttons = genres.map((genre) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "genre-button";
    button.dataset.genreId = genre.id;
    button.setAttribute("aria-pressed", "false");
    if (genre.icon) {
      const icon = document.createElement("span");
      icon.className = "genre-button__icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = genre.icon;
      button.append(icon);
    }
    button.append(genre.label);
    button.addEventListener("click", () => onSelect(genre));
    return button;
  });
  container.replaceChildren(...buttons);

  return {
    setActive(genreId) {
      for (const button of buttons) {
        const active = button.dataset.genreId === genreId;
        button.setAttribute("aria-pressed", String(active));
        button.classList.toggle("genre-button--active", active);
      }
    },
  };
}
