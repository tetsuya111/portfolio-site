import "./styles.css";
import rawConfig from "./config/map-config.json";
import { createApp, type App } from "./app";
import { ConfigError, parseMapConfig, type Genre, type MapConfig } from "./config/parseMapConfig";
import { readApiSettings } from "./env";
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

  // 1. 設定ファイルを検証する（FR-4.2）
  let config: MapConfig;
  try {
    config = parseMapConfig(rawConfig);
  } catch (error) {
    if (!(error instanceof ConfigError)) throw error;
    status.error("設定ファイル（src/config/map-config.json）に誤りがあります。", error.problems);
    mapEl.dataset.state = "unavailable";
    return;
  }
  byId("area-name").textContent = config.area.name;

  // 2. ジャンルボタン（地図が使えなくても構成は見えるようにする）。
  //    地図の準備中に押されたジャンルは覚えておき、準備ができたらそのジャンルから表示する。
  let app: App | null = null;
  let requestedGenre: Genre | undefined;
  const bar = createGenreBar(byId("genres"), config.genres, (genre) => {
    if (app) {
      void app.selectGenre(genre);
    } else {
      requestedGenre = genre;
      bar.setActive(genre.id);
    }
  });

  /** 地図が使えないことを表示し、以降の操作と表示更新を止める（FR-5.3, FR-5.4） */
  const markMapUnavailable = (message: string, details?: string[]) => {
    app?.disable();
    bar.setDisabled(true);
    status.error(message, details);
    mapEl.dataset.state = "unavailable";
  };

  // 3. APIキー（FR-5.3）
  const settings = readApiSettings(import.meta.env);
  if (!settings) {
    markMapUnavailable("Google Maps の APIキーが設定されていません。", [
      "env.template を .env という名前でコピーし、VITE_GOOGLE_MAPS_API_KEY を設定してから開発サーバーを再起動してください（手順は README.md）。",
    ]);
    return;
  }

  // 4. Maps JavaScript API を読み込み、地図を1回だけ作る（FR-5.4, FR-2.3）
  let authFailed = false;
  try {
    const libs = await createGoogleMapsLoader()({
      apiKey: settings.apiKey,
      onAuthFailure: () => {
        authFailed = true;
        markMapUnavailable("Google マップの認証に失敗しました。APIキーとその制限設定を確認してください。");
      },
    });
    if (authFailed) return;
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
      layer: createMarkerLayer({
        map,
        marker: libs.marker,
        core: libs.core,
        defaultView: { center: config.area.center, zoom: config.area.zoom },
      }),
      status,
      detail,
      setActiveGenre: (id) => bar.setActive(id),
    });
  } catch (error) {
    console.error(error);
    markMapUnavailable(error instanceof Error ? error.message : "Google マップを読み込めませんでした。");
    return;
  }

  // 5. 準備中に押されたジャンル、なければ先頭のジャンルから表示する（FR-1.2）
  await app.start(requestedGenre);
}

void main();
