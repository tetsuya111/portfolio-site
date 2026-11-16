import { describe, expect, test, vi } from "vitest";
import type { Genre } from "../config/parseMapConfig";
import { cacheByGenre } from "./shopCache";
import type { Shop } from "./shop";

const ramen: Genre = { id: "ramen", label: "ラーメン", query: "q1" };
const cafe: Genre = { id: "cafe", label: "カフェ", query: "q2" };
const shop = (id: string): Shop => ({ id, name: id, address: "", location: { lat: 0, lng: 0 }, googleMapsUrl: "https://x/" });

describe("cacheByGenre", () => {
  test("同じジャンルは1回だけ検索する", async () => {
    const search = vi.fn(async (g: Genre) => [shop(g.id)]);
    const cached = cacheByGenre(search);
    expect(await cached(ramen)).toEqual([shop("ramen")]);
    expect(await cached(ramen)).toEqual([shop("ramen")]);
    expect(search).toHaveBeenCalledTimes(1);
  });

  test("検索中に同じジャンルが呼ばれても1回だけ検索する", async () => {
    const search = vi.fn(async (g: Genre) => [shop(g.id)]);
    const cached = cacheByGenre(search);
    await Promise.all([cached(ramen), cached(ramen)]);
    expect(search).toHaveBeenCalledTimes(1);
  });

  test("別のジャンルは別に検索する", async () => {
    const search = vi.fn(async (g: Genre) => [shop(g.id)]);
    const cached = cacheByGenre(search);
    await cached(ramen);
    expect(await cached(cafe)).toEqual([shop("cafe")]);
    expect(search).toHaveBeenCalledTimes(2);
  });

  test("失敗した検索は保持せず、次回は再検索する", async () => {
    const search = vi
      .fn<(g: Genre) => Promise<Shop[]>>()
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce([shop("ramen")]);
    const cached = cacheByGenre(search);
    await expect(cached(ramen)).rejects.toThrow("network");
    expect(await cached(ramen)).toEqual([shop("ramen")]);
    expect(search).toHaveBeenCalledTimes(2);
  });
});
