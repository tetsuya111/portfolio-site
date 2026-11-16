import type { Shop } from "../places/shop";

export interface ShopDetail {
  show(shop: Shop): void;
  /** プログラムから閉じる（onClose は呼ばない） */
  hide(): void;
  isOpen(): boolean;
}

export interface ShopDetailOptions {
  /** 閲覧者が「閉じる」ボタンや Escape キーで閉じたときに呼ばれる */
  onClose: () => void;
}

/** 要素を作り、文字列は textContent で入れる（Google から来た文字列を HTML として解釈しない） */
function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className: string,
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  if (className) el.className = className;
  el.append(...children);
  return el;
}

function externalLink(href: string, text: string, className = ""): HTMLAnchorElement {
  const a = h("a", className, text);
  a.href = href;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  return a;
}

function formatRating(rating: number, count?: number): string {
  const stars = `★ ${rating.toFixed(1)}`;
  return count === undefined ? stars : `${stars}（${count.toLocaleString("ja-JP")}件の口コミ）`;
}

function render(shop: Shop, closeButton: HTMLButtonElement): Node[] {
  const header = h("header", "shop-detail__header", h("h2", "shop-detail__name", shop.name), closeButton);
  const body: Node[] = [header];
  if (shop.address) body.push(h("p", "shop-detail__address", shop.address));
  if (shop.rating !== undefined) {
    body.push(h("p", "shop-detail__rating", formatRating(shop.rating, shop.userRatingCount)));
  }
  if (shop.phoneNumber) {
    const tel = h("a", "", shop.phoneNumber);
    tel.href = `tel:${shop.phoneNumber.replace(/[^\d+]/g, "")}`;
    body.push(h("p", "shop-detail__phone", "電話: ", tel));
  }
  if (shop.websiteUrl) {
    body.push(h("p", "shop-detail__website", externalLink(shop.websiteUrl, "Webサイト")));
  }
  if (shop.openingHours) {
    body.push(
      h(
        "section",
        "shop-detail__hours",
        h("h3", "", "営業時間"),
        h("ul", "", ...shop.openingHours.map((line) => h("li", "", line))),
      ),
    );
  }
  body.push(externalLink(shop.googleMapsUrl, "Googleマップで開く", "shop-detail__maps-link"));
  body.push(h("p", "shop-detail__attribution", "情報提供: Google"));
  return body;
}

/** ピンを押したときに店舗の詳細を表示するパネル */
export function createShopDetail(el: HTMLElement, { onClose }: ShopDetailOptions): ShopDetail {
  el.hidden = true;
  el.classList.add("shop-detail");
  el.setAttribute("aria-label", "お店の詳細");

  const hide = () => {
    el.hidden = true;
    el.replaceChildren();
  };
  const closeByUser = () => {
    if (el.hidden) return;
    hide();
    onClose();
  };

  el.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeByUser();
  });

  return {
    show(shop) {
      const closeButton = h("button", "shop-detail__close", "×");
      closeButton.type = "button";
      closeButton.setAttribute("aria-label", "閉じる");
      closeButton.addEventListener("click", closeByUser);
      el.replaceChildren(...render(shop, closeButton));
      el.hidden = false;
      closeButton.focus();
    },
    hide,
    isOpen: () => !el.hidden,
  };
}
