import "./styles.css";
import rawConfig from "./config/map-config.json";
import { createApp, type App } from "./app";
import { ConfigError, parseMapConfig, type MapConfig } from "./config/parseMapConfig";
import { readApiSettings } from "./env";
import type { GoogleLibraries } from "./maps/googleTypes";
import { createGoogleMapsLoader } from "./maps/loadGoogleMaps";
import { createMarkerLayer } from "./maps/markerLayer";
import { createShopSearcher } from "./places/searchShops";
import { cacheByGenre } from "./places/shopCache";
import { createGenreBar } from "./ui/genreBar";
import { createShopDetail } from "./ui/shopDetail";
import { createStatusView } from "./ui/statusView";

function byId(id: string): HTMLElement {
  const el = document.getElementById(id);
  if (!el) throw new Error(`#${id} が index.html にありません`);
  return el;
}

async function main(): Promise<void> {
  const status = createStatusView(byId("status"));
  const mapEl = byId("map");
  const markMapUnavailable = (message: string, details?: string[]) => {
    status.error(message, details);
    mapEl.dataset.state = "unavailable";
  };

  // 1. 設定ファイルを検証する（FR-4.2）
  let config: MapConfig;
  try {
    config = parseMapConfig(rawConfig);
  } catch (error) {
    if (!(error instanceof ConfigError)) throw error;
    markMapUnavailable("設定ファイル（src/config/map-config.json）に誤りがあります。", error.problems);
    return;
  }
  byId("area-name").textContent = config.area.name;

  // 2. ジャンルボタン（地図が使えなくても構成は見えるようにする）
  let app: App | null = null;
  const bar = createGenreBar(byId("genres"), config.genres, (genre) => void app?.selectGenre(genre));

  // 3. APIキー（FR-5.3）
  const settings = readApiSettings(import.meta.env);
  if (!settings) {
    markMapUnavailable("Google Maps の APIキーが設定されていません。", [
      "env.template を .env という名前でコピーし、VITE_GOOGLE_MAPS_API_KEY を設定してから開発サーバーを再起動してください（手順は README.md）。",
    ]);
    return;
  }

  // 4. Maps JavaScript API を読み込む（FR-5.4）
  let libs: GoogleLibraries;
  try {
    libs = await createGoogleMapsLoader()({
      apiKey: settings.apiKey,
      onAuthFailure: () =>
        markMapUnavailable("Google マップの認証に失敗しました。APIキーとその制限設定を確認してください。"),
    });
  } catch (error) {
    console.error(error);
    markMapUnavailable(error instanceof Error ? error.message : "Google マップを読み込めませんでした。");
    return;
  }

  // 5. 地図は1回だけ作り、ジャンルを切り替えても使い続ける（FR-2.3）
  const map = new libs.maps.Map(mapEl, {
    center: config.area.center,
    zoom: config.area.zoom,
    mapId: settings.mapId,
    clickableIcons: false,
  });
  const detail = createShopDetail(byId("detail"), { onClose: () => app?.handleDetailClosed() });
  app = createApp({
    genres: config.genres,
    search: cacheByGenre(createShopSearcher(libs.places, config.area)),
    layer: createMarkerLayer({ map, marker: libs.marker, core: libs.core }),
    status,
    detail,
    setActiveGenre: (id) => bar.setActive(id),
  });
  await app.start();
}

void main();
