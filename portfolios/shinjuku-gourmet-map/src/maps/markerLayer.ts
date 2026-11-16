import type { Shop } from "../places/shop";
import type {
  AdvancedMarker,
  CoreLibrary,
  GoogleMap,
  LatLngLiteral,
  MapListener,
  MarkerLibrary,
} from "./googleTypes";

/** 全ピンを収めるときの地図の余白（px） */
const FIT_PADDING = 48;
/** 検索結果が1件のときのズーム（店の周辺が分かる縮尺） */
export const SINGLE_SHOP_ZOOM = 17;
/** 店舗がこの範囲（度、約50m）に収まっていれば1か所とみなす（fitBounds が最大ズームになるのを避ける） */
const SAME_PLACE_DEGREES = 0.0005;

export interface MarkerLayer {
  /** 前のピンを消し、店舗ごとにピンを描いて表示範囲を合わせる */
  show(shops: Shop[], onSelect: (shop: Shop) => void): void;
  clear(): void;
  /** 指定した店舗のピンだけを強調する（null で解除） */
  highlight(shopId: string | null): void;
}

interface Dependencies {
  map: GoogleMap;
  marker: MarkerLibrary;
  core: CoreLibrary;
  /** 検索結果が0件のときに戻す表示（エリアの中心と初期ズーム） */
  defaultView: { center: LatLngLiteral; zoom: number };
}

interface Pin {
  shopId: string;
  marker: AdvancedMarker;
  listener: MapListener | null;
  element: HTMLElement;
}

function createPinElement(): HTMLElement {
  const el = document.createElement("div");
  el.className = "pin";
  return el;
}

export function createMarkerLayer({ map, marker, core, defaultView }: Dependencies): MarkerLayer {
  let pins: Pin[] = [];

  const clear = () => {
    for (const pin of pins) {
      pin.listener?.remove();
      pin.marker.map = null;
    }
    pins = [];
  };

  return {
    show(shops, onSelect) {
      clear();
      // 途中で例外が起きても clear で消せるよう、作ったピンはすぐ pins に入れる
      for (const shop of shops) {
        const element = createPinElement();
        const pin: Pin = {
          shopId: shop.id,
          marker: new marker.AdvancedMarkerElement({
            map,
            position: shop.location,
            title: shop.name,
            content: element,
            gmpClickable: true,
          }),
          listener: null,
          element,
        };
        pins.push(pin);
        pin.listener = pin.marker.addListener("click", () => onSelect(shop));
      }

      if (shops.length === 0) {
        map.panTo(defaultView.center);
        map.setZoom(defaultView.zoom);
        return;
      }
      const lats = shops.map((s) => s.location.lat);
      const lngs = shops.map((s) => s.location.lng);
      const [south, north, west, east] = [Math.min(...lats), Math.max(...lats), Math.min(...lngs), Math.max(...lngs)];
      if (north - south < SAME_PLACE_DEGREES && east - west < SAME_PLACE_DEGREES) {
        map.panTo({ lat: (south + north) / 2, lng: (west + east) / 2 });
        map.setZoom(Math.max(SINGLE_SHOP_ZOOM, defaultView.zoom));
      } else {
        const bounds = new core.LatLngBounds();
        for (const shop of shops) bounds.extend(shop.location);
        map.fitBounds(bounds, FIT_PADDING);
      }
    },
    clear,
    highlight(shopId) {
      for (const pin of pins) {
        pin.element.classList.toggle("pin--selected", pin.shopId === shopId);
      }
    },
  };
}
