import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { Shop } from "../places/shop";
import { createShopDetail } from "./shopDetail";

const fullShop = (): Shop => ({
  id: "p1",
  name: "麺屋テスト",
  address: "東京都新宿区1-1",
  location: { lat: 0, lng: 0 },
  rating: 4.25,
  userRatingCount: 1234,
  openingHours: ["月曜日: 11時00分～22時00分", "火曜日: 定休日"],
  phoneNumber: "03-1234-5678",
  websiteUrl: "https://example.com/",
  googleMapsUrl: "https://maps.google.com/?cid=1",
});
const minimalShop = (): Shop => ({
  id: "p2",
  name: "最小の店",
  address: "東京都新宿区2-2",
  location: { lat: 0, lng: 0 },
  googleMapsUrl: "https://maps.google.com/?cid=2",
});

let el: HTMLElement;
beforeEach(() => {
  el = document.createElement("aside");
  document.body.append(el);
});
afterEach(() => el.remove());

const q = (selector: string) => el.querySelector(selector);

describe("createShopDetail", () => {
  test("最初は非表示", () => {
    createShopDetail(el, { onClose: () => {} });
    expect(el.hidden).toBe(true);
  });

  test("店名・住所を表示する", () => {
    createShopDetail(el, { onClose: () => {} }).show(fullShop());
    expect(el.hidden).toBe(false);
    expect(q("h2")?.textContent).toBe("麺屋テスト");
    expect(q(".shop-detail__address")?.textContent).toBe("東京都新宿区1-1");
  });

  test("評価・口コミ件数・営業時間・電話・Webサイトを表示する", () => {
    createShopDetail(el, { onClose: () => {} }).show(fullShop());
    expect(q(".shop-detail__rating")?.textContent).toBe("★ 4.3（1,234件の口コミ）");
    expect([...el.querySelectorAll(".shop-detail__hours li")].map((li) => li.textContent)).toEqual([
      "月曜日: 11時00分～22時00分",
      "火曜日: 定休日",
    ]);
    const tel = q(".shop-detail__phone a") as HTMLAnchorElement;
    expect(tel.textContent).toBe("03-1234-5678");
    expect(tel.getAttribute("href")).toBe("tel:0312345678");
    const site = q(".shop-detail__website a") as HTMLAnchorElement;
    expect(site.href).toBe("https://example.com/");
  });

  test("情報がない項目は表示しない", () => {
    createShopDetail(el, { onClose: () => {} }).show(minimalShop());
    for (const selector of [".shop-detail__rating", ".shop-detail__hours", ".shop-detail__phone", ".shop-detail__website"]) {
      expect(q(selector)).toBeNull();
    }
  });

  test("口コミ件数がなくても評価は表示する", () => {
    createShopDetail(el, { onClose: () => {} }).show({ ...minimalShop(), rating: 3 });
    expect(q(".shop-detail__rating")?.textContent).toBe("★ 3.0");
  });

  test("Googleマップへのリンクを新しいタブで開く", () => {
    createShopDetail(el, { onClose: () => {} }).show(fullShop());
    const link = q(".shop-detail__maps-link") as HTMLAnchorElement;
    expect(link.textContent).toBe("Googleマップで開く");
    expect(link.href).toBe("https://maps.google.com/?cid=1");
    expect(link.target).toBe("_blank");
    expect(link.rel).toBe("noopener noreferrer");
  });

  test("Google の情報であることを表示する", () => {
    createShopDetail(el, { onClose: () => {} }).show(fullShop());
    expect(q(".shop-detail__attribution")?.textContent).toBe("情報提供: Google");
  });

  test("HTML を含む店名を文字列として表示する", () => {
    createShopDetail(el, { onClose: () => {} }).show({ ...fullShop(), name: "<img src=x onerror=alert(1)>" });
    expect(q("h2")?.textContent).toBe("<img src=x onerror=alert(1)>");
    expect(q("img")).toBeNull();
  });

  test("開いたら閉じるボタンにフォーカスする", () => {
    createShopDetail(el, { onClose: () => {} }).show(fullShop());
    expect(document.activeElement).toBe(q(".shop-detail__close"));
  });

  test("閉じるボタンで非表示にして onClose を呼ぶ", () => {
    const onClose = vi.fn();
    const detail = createShopDetail(el, { onClose });
    detail.show(fullShop());
    (q(".shop-detail__close") as HTMLButtonElement).click();
    expect(el.hidden).toBe(true);
    expect(onClose).toHaveBeenCalledOnce();
  });

  test("Escape キーでも閉じる", () => {
    const onClose = vi.fn();
    createShopDetail(el, { onClose }).show(fullShop());
    el.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(el.hidden).toBe(true);
    expect(onClose).toHaveBeenCalledOnce();
  });

  test("hide はプログラムからの非表示で onClose を呼ばない", () => {
    const onClose = vi.fn();
    const detail = createShopDetail(el, { onClose });
    detail.show(fullShop());
    detail.hide();
    expect(el.hidden).toBe(true);
    expect(onClose).not.toHaveBeenCalled();
  });

  test("別の店を開くと内容が入れ替わる", () => {
    const detail = createShopDetail(el, { onClose: () => {} });
    detail.show(fullShop());
    detail.show(minimalShop());
    expect(el.querySelectorAll("h2")).toHaveLength(1);
    expect(q("h2")?.textContent).toBe("最小の店");
  });

  test("閲覧者が閉じたら、開く前にフォーカスしていた要素へ戻す", () => {
    const opener = document.createElement("button");
    document.body.append(opener);
    opener.focus();
    const detail = createShopDetail(el, { onClose: () => {} });
    detail.show(fullShop());
    detail.show(minimalShop());
    (q(".shop-detail__close") as HTMLButtonElement).click();
    expect(document.activeElement).toBe(opener);
    opener.remove();
  });
});
