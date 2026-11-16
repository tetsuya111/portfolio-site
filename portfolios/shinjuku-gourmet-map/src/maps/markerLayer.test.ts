import { describe, expect, test, vi } from "vitest";
import type {
  AdvancedMarkerOptions,
  GoogleMap,
  LatLngBoundsObject,
  LatLngLiteral,
} from "./googleTypes";
import type { Shop } from "../places/shop";
import { createMarkerLayer, SINGLE_SHOP_ZOOM } from "./markerLayer";

class FakeMarker {
  static created: FakeMarker[] = [];
  map: GoogleMap | null;
  handler: (() => void) | null = null;
  removed = false;
  constructor(readonly options: AdvancedMarkerOptions) {
    this.map = options.map;
    FakeMarker.created.push(this);
  }
  addListener(_event: "click", handler: () => void) {
    this.handler = handler;
    return { remove: () => (this.removed = true) };
  }
}

class FakeBounds implements LatLngBoundsObject {
  points: LatLngLiteral[] = [];
  extend(p: LatLngLiteral) {
    this.points.push(p);
    return this;
  }
}

function setup(zoom = 15) {
  FakeMarker.created = [];
  const map = { fitBounds: vi.fn(), panTo: vi.fn(), setZoom: vi.fn() };
  const layer = createMarkerLayer({
    map,
    marker: { AdvancedMarkerElement: FakeMarker },
    core: { LatLngBounds: FakeBounds },
    defaultView: { center: { lat: 35, lng: 139 }, zoom },
  });
  return { map, layer };
}

const shop = (id: string, lat = 35.69, lng = 139.7): Shop => ({
  id,
  name: `店${id}`,
  address: "",
  location: { lat, lng },
  googleMapsUrl: "https://x/",
});

describe("createMarkerLayer", () => {
  test("店舗ごとにクリックできるピンを作る", () => {
    const { map, layer } = setup();
    layer.show([shop("a"), shop("b", 35.7, 139.71)], () => {});
    expect(FakeMarker.created).toHaveLength(2);
    const [first] = FakeMarker.created;
    expect(first.options.map).toBe(map);
    expect(first.options.position).toEqual({ lat: 35.69, lng: 139.7 });
    expect(first.options.title).toBe("店a");
    expect(first.options.gmpClickable).toBe(true);
    expect(first.options.content.classList.contains("pin")).toBe(true);
  });

  test("ピンのクリックで店舗を通知する", () => {
    const { layer } = setup();
    const onSelect = vi.fn();
    layer.show([shop("a"), shop("b")], onSelect);
    FakeMarker.created[1].handler?.();
    expect(onSelect).toHaveBeenCalledWith(shop("b"));
  });

  test("複数件なら全ピンが収まるよう表示範囲を合わせる", () => {
    const { map, layer } = setup();
    layer.show([shop("a", 1, 2), shop("b", 3, 4)], () => {});
    expect(map.fitBounds).toHaveBeenCalledOnce();
    const bounds = map.fitBounds.mock.calls[0][0] as FakeBounds;
    expect(bounds.points).toEqual([
      { lat: 1, lng: 2 },
      { lat: 3, lng: 4 },
    ]);
  });

  test("1件ならその店に寄って拡大する（前のジャンルの縮尺を引き継がない）", () => {
    const { map, layer } = setup();
    layer.show([shop("a", 1, 2)], () => {});
    expect(map.panTo).toHaveBeenCalledWith({ lat: 1, lng: 2 });
    expect(map.setZoom).toHaveBeenCalledWith(SINGLE_SHOP_ZOOM);
    expect(map.fitBounds).not.toHaveBeenCalled();
  });

  test("0件ならエリアの初期表示に戻す", () => {
    const { map, layer } = setup();
    layer.show([], () => {});
    expect(map.panTo).toHaveBeenCalledWith({ lat: 35, lng: 139 });
    expect(map.setZoom).toHaveBeenCalledWith(15);
    expect(map.fitBounds).not.toHaveBeenCalled();
  });

  test("clear で全ピンを地図から外し、リスナーも外す", () => {
    const { layer } = setup();
    layer.show([shop("a"), shop("b")], () => {});
    layer.clear();
    expect(FakeMarker.created.every((m) => m.map === null && m.removed)).toBe(true);
  });

  test("show は前のピンを消してから描く", () => {
    const { layer } = setup();
    layer.show([shop("a")], () => {});
    const [old] = FakeMarker.created;
    layer.show([shop("b")], () => {});
    expect(old.map).toBeNull();
  });

  test("highlight で選択中のピンだけ強調する", () => {
    const { layer } = setup();
    layer.show([shop("a"), shop("b")], () => {});
    const selected = () => FakeMarker.created.map((m) => m.options.content.classList.contains("pin--selected"));
    layer.highlight("b");
    expect(selected()).toEqual([false, true]);
    layer.highlight("a");
    expect(selected()).toEqual([true, false]);
    layer.highlight(null);
    expect(selected()).toEqual([false, false]);
  });

  test("1件のときも設定の初期ズームより引いた表示にはしない", () => {
    const { map, layer } = setup(19);
    layer.show([shop("a")], () => {});
    expect(map.setZoom).toHaveBeenCalledWith(19);
  });

  test("ピンの作成が途中で失敗しても、作成済みのピンは clear で消せる", () => {
    const { layer } = setup();
    const original = FakeMarker.prototype.addListener;
    let count = 0;
    FakeMarker.prototype.addListener = function (this: FakeMarker, e: "click", h: () => void) {
      if (++count === 2) throw new Error("marker");
      return original.call(this, e, h);
    };
    try {
      expect(() => layer.show([shop("a"), shop("b"), shop("c")], () => {})).toThrow("marker");
    } finally {
      FakeMarker.prototype.addListener = original;
    }
    layer.clear();
    expect(FakeMarker.created.every((m) => m.map === null)).toBe(true);
  });
});
