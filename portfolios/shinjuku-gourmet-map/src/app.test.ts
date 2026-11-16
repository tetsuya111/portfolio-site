import { describe, expect, test, vi } from "vitest";
import { createApp } from "./app";
import type { Genre } from "./config/parseMapConfig";
import type { Shop } from "./places/shop";

const ramen: Genre = { id: "ramen", label: "ラーメン", query: "q1" };
const cafe: Genre = { id: "cafe", label: "カフェ", query: "q2" };
const shop = (id: string): Shop => ({ id, name: id, address: "", location: { lat: 0, lng: 0 }, googleMapsUrl: "https://x/" });

/** 解決のタイミングをテストから制御できる Promise */
function deferred<T>() {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function setup(search = vi.fn(async (g: Genre) => [shop(`${g.id}-1`), shop(`${g.id}-2`)])) {
  const deps = {
    genres: [ramen, cafe],
    search,
    layer: { show: vi.fn(), clear: vi.fn(), highlight: vi.fn() },
    status: { loading: vi.fn(), result: vi.fn(), error: vi.fn() },
    detail: { show: vi.fn(), hide: vi.fn(), isOpen: vi.fn(() => false) },
    setActiveGenre: vi.fn(),
  };
  return { deps, app: createApp(deps) };
}

/** layer.show に渡された onSelect でピンを押したことにする */
function clickPin(deps: ReturnType<typeof setup>["deps"], index: number) {
  const [shops, onSelect] = deps.layer.show.mock.lastCall as [Shop[], (s: Shop) => void];
  onSelect(shops[index]);
  return shops[index];
}

describe("createApp", () => {
  test("start で先頭のジャンルを選んで検索する", async () => {
    const { deps, app } = setup();
    await app.start();
    expect(deps.setActiveGenre).toHaveBeenCalledWith("ramen");
    expect(deps.search).toHaveBeenCalledWith(ramen);
    expect(deps.layer.show).toHaveBeenCalledWith([shop("ramen-1"), shop("ramen-2")], expect.any(Function));
    expect(deps.status.result).toHaveBeenCalledWith(ramen, 2);
  });

  test("検索中は読み込み中を表示する", async () => {
    const pending = deferred<Shop[]>();
    const { deps, app } = setup(vi.fn(() => pending.promise));
    const done = app.selectGenre(cafe);
    expect(deps.status.loading).toHaveBeenCalledWith(cafe);
    expect(deps.status.result).not.toHaveBeenCalled();
    pending.resolve([]);
    await done;
    expect(deps.status.result).toHaveBeenCalledWith(cafe, 0);
  });

  test("ジャンルを切り替えると前のピンを消し、詳細を閉じる", async () => {
    const { deps, app } = setup();
    await app.start();
    deps.layer.clear.mockClear();
    await app.selectGenre(cafe);
    expect(deps.layer.clear).toHaveBeenCalled();
    expect(deps.detail.hide).toHaveBeenCalled();
    expect(deps.setActiveGenre).toHaveBeenLastCalledWith("cafe");
    expect(deps.layer.show).toHaveBeenLastCalledWith([shop("cafe-1"), shop("cafe-2")], expect.any(Function));
  });

  test("検索に失敗したらエラーを表示し、別のジャンルは選べる", async () => {
    const search = vi
      .fn<(g: Genre) => Promise<Shop[]>>()
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce([shop("cafe-1")]);
    const { deps, app } = setup(search);
    vi.spyOn(console, "error").mockImplementation(() => {});
    await app.selectGenre(ramen);
    expect(deps.status.error).toHaveBeenCalledWith(
      "ラーメンのお店を読み込めませんでした。時間をおいてもう一度お試しください。",
    );
    expect(deps.layer.show).not.toHaveBeenCalled();
    await app.selectGenre(cafe);
    expect(deps.status.result).toHaveBeenCalledWith(cafe, 1);
  });

  test("検索中に別のジャンルが押されたら、最後のジャンルの結果だけを表示する", async () => {
    const slow = deferred<Shop[]>();
    const search = vi.fn((g: Genre) => (g.id === "ramen" ? slow.promise : Promise.resolve([shop("cafe-1")])));
    const { deps, app } = setup(search);
    const first = app.selectGenre(ramen);
    await app.selectGenre(cafe);
    slow.resolve([shop("ramen-1")]);
    await first;
    expect(deps.layer.show).toHaveBeenCalledTimes(1);
    expect(deps.layer.show).toHaveBeenCalledWith([shop("cafe-1")], expect.any(Function));
    expect(deps.status.result).toHaveBeenCalledTimes(1);
  });

  test("古いジャンルの検索が後から失敗してもエラーを出さない", async () => {
    const slow = deferred<Shop[]>();
    const search = vi.fn((g: Genre) => (g.id === "ramen" ? slow.promise : Promise.resolve([shop("cafe-1")])));
    const { deps, app } = setup(search);
    const first = app.selectGenre(ramen);
    await app.selectGenre(cafe);
    slow.reject(new Error("late"));
    await first;
    expect(deps.status.error).not.toHaveBeenCalled();
  });

  test("ピンを押すと詳細を表示し、そのピンを強調する", async () => {
    const { deps, app } = setup();
    await app.start();
    const clicked = clickPin(deps, 1);
    expect(deps.detail.show).toHaveBeenCalledWith(clicked);
    expect(deps.layer.highlight).toHaveBeenLastCalledWith("ramen-2");
  });

  test("詳細が閉じられたらピンの強調を解除する", async () => {
    const { deps, app } = setup();
    await app.start();
    clickPin(deps, 0);
    app.handleDetailClosed();
    expect(deps.layer.highlight).toHaveBeenLastCalledWith(null);
  });

  test("ジャンルが0件なら start は何もしない", async () => {
    const { deps, app } = setup();
    deps.genres.length = 0;
    await app.start();
    expect(deps.search).not.toHaveBeenCalled();
  });
});
