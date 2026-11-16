import { describe, expect, test, vi } from "vitest";
import type { AreaConfig, Genre } from "../config/parseMapConfig";
import type { PlaceLike } from "../maps/googleTypes";
import {
  boundsAround,
  buildSearchRequest,
  createShopSearcher,
  MAX_RESULTS,
  toShop,
} from "./searchShops";

const area: AreaConfig = { name: "新宿", center: { lat: 35.69, lng: 139.7 }, radiusMeters: 1500, zoom: 15 };
const genre: Genre = { id: "ramen", label: "ラーメン", query: "新宿 ラーメン" };

const latLng = (lat: number, lng: number) => ({ lat: () => lat, lng: () => lng });

const fullPlace = (): PlaceLike => ({
  id: "p1",
  displayName: "麺屋テスト",
  formattedAddress: "東京都新宿区1-1",
  location: latLng(35.691, 139.701),
  rating: 4.2,
  userRatingCount: 321,
  regularOpeningHours: { weekdayDescriptions: ["月曜日: 11時00分～22時00分"] },
  nationalPhoneNumber: "03-0000-0000",
  websiteURI: "https://example.com/",
  googleMapsURI: "https://maps.google.com/?cid=1",
});

describe("boundsAround", () => {
  test("中心から半径ぶん離れた矩形を返す", () => {
    const b = boundsAround({ lat: 35, lng: 139 }, 1110);
    expect(b.north - 35).toBeCloseTo(0.01, 3);
    expect(35 - b.south).toBeCloseTo(0.01, 3);
    // 経度1度の距離は緯度によって縮むので、緯度より広くなる
    expect(b.east - 139).toBeGreaterThan(0.01);
    expect(b.east - 139).toBeCloseTo(139 - b.west, 9);
  });
});

test("経度は -180〜180 に収める", () => {
  const b = boundsAround({ lat: 0, lng: 179.99 }, 5000);
  expect(b.east).toBe(180);
  expect(boundsAround({ lat: 0, lng: -179.99 }, 5000).west).toBe(-180);
});

describe("buildSearchRequest", () => {
  test("ジャンルのクエリ・エリア・取得項目・件数上限を指定する", () => {
    const req = buildSearchRequest(genre, area);
    expect(req.textQuery).toBe("新宿 ラーメン");
    expect(req.maxResultCount).toBe(MAX_RESULTS);
    expect(MAX_RESULTS).toBe(20);
    expect(req.language).toBe("ja");
    expect(req.region).toBe("jp");
    expect(req.locationRestriction).toEqual(boundsAround(area.center, area.radiusMeters));
    expect(req.fields).toEqual(
      expect.arrayContaining(["id", "displayName", "formattedAddress", "location", "googleMapsURI"]),
    );
  });
});

describe("toShop", () => {
  test("すべての項目を変換する", () => {
    expect(toShop(fullPlace())).toEqual({
      id: "p1",
      name: "麺屋テスト",
      address: "東京都新宿区1-1",
      location: { lat: 35.691, lng: 139.701 },
      rating: 4.2,
      userRatingCount: 321,
      openingHours: ["月曜日: 11時00分～22時00分"],
      phoneNumber: "03-0000-0000",
      websiteUrl: "https://example.com/",
      googleMapsUrl: "https://maps.google.com/?cid=1",
    });
  });

  test("任意項目がなければ含めない", () => {
    const shop = toShop({ id: "p2", displayName: "店", location: latLng(1, 2), regularOpeningHours: null });
    expect(shop).not.toBeNull();
    expect(Object.keys(shop!).sort()).toEqual(["address", "googleMapsUrl", "id", "location", "name"]);
    expect(shop!.address).toBe("");
  });

  test("位置がなければ null", () => {
    expect(toShop({ ...fullPlace(), location: null })).toBeNull();
  });

  test("Googleマップの URL がなければ店名と ID から組み立てる", () => {
    const shop = toShop({ ...fullPlace(), googleMapsURI: null });
    const url = new URL(shop!.googleMapsUrl);
    expect(url.origin + url.pathname).toBe("https://www.google.com/maps/search/");
    expect(url.searchParams.get("query")).toBe("麺屋テスト");
    expect(url.searchParams.get("query_place_id")).toBe("p1");
  });

  test("http(s) 以外の URL は捨てる", () => {
    const shop = toShop({ ...fullPlace(), websiteURI: "javascript:alert(1)", googleMapsURI: "data:text/html,x" });
    expect(shop!.websiteUrl).toBeUndefined();
    expect(shop!.googleMapsUrl.startsWith("https://www.google.com/maps/search/")).toBe(true);
  });

  test("店名がなければ「名称不明」とする", () => {
    expect(toShop({ ...fullPlace(), displayName: null })!.name).toBe("名称不明");
  });
});

describe("createShopSearcher", () => {
  test("Text Search を呼び、位置のある店舗だけを返す", async () => {
    const searchByText = vi.fn(async () => ({
      places: [fullPlace(), { id: "nowhere", displayName: "位置なし" }],
    }));
    const search = createShopSearcher({ Place: { searchByText } }, area);
    const shops = await search(genre);
    expect(searchByText).toHaveBeenCalledWith(buildSearchRequest(genre, area));
    expect(shops.map((s) => s.id)).toEqual(["p1"]);
  });
});
