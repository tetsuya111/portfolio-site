import type { Genre } from "../config/parseMapConfig";

export interface StatusView {
  loading(genre: Genre): void;
  result(genre: Genre, count: number): void;
  error(message: string, details?: string[]): void;
}

/** 読み込み中・件数・エラーを表示する領域 */
export function createStatusView(el: HTMLElement): StatusView {
  el.setAttribute("role", "status");
  el.setAttribute("aria-live", "polite");

  const show = (state: string, ...nodes: (Node | string)[]) => {
    el.dataset.state = state;
    el.replaceChildren(...nodes);
  };

  return {
    loading(genre) {
      show("loading", `${genre.label}のお店を探しています…`);
    },
    result(genre, count) {
      if (count === 0) show("empty", `${genre.label}: お店が見つかりませんでした`);
      else show("result", `${genre.label}: ${count}件`);
    },
    error(message, details = []) {
      if (details.length === 0) {
        show("error", message);
        return;
      }
      const p = document.createElement("p");
      p.textContent = message;
      const ul = document.createElement("ul");
      ul.append(
        ...details.map((d) => {
          const li = document.createElement("li");
          li.textContent = d;
          return li;
        }),
      );
      show("error", p, ul);
    },
  };
}
