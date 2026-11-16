import { describe, expect, test } from "vitest";
import { DEMO_MAP_ID, readApiSettings } from "./env";

describe("readApiSettings", () => {
  test("APIキーと Map ID を返す", () => {
    expect(
      readApiSettings({ VITE_GOOGLE_MAPS_API_KEY: " key-123 ", VITE_GOOGLE_MAPS_MAP_ID: "map-1" }),
    ).toEqual({ apiKey: "key-123", mapId: "map-1" });
  });

  test.each([undefined, "", "   "])("APIキーが %j なら null", (key) => {
    expect(readApiSettings({ VITE_GOOGLE_MAPS_API_KEY: key })).toBeNull();
  });

  test("Map ID が未設定ならデモ用IDを使う", () => {
    expect(readApiSettings({ VITE_GOOGLE_MAPS_API_KEY: "k", VITE_GOOGLE_MAPS_MAP_ID: " " })).toEqual({
      apiKey: "k",
      mapId: DEMO_MAP_ID,
    });
  });
});
