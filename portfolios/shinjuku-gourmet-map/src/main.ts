import "./styles.css";
import rawConfig from "./config/map-config.json";
import { createApp, type App } from "./app";
import { ConfigError, parseMapConfig, type Genre, type MapConfig } from "./config/parseMapConfig";
import { readApiSettings } from "./env";
import type { GoogleLibraries, GoogleMap } from "./maps/googleTypes";
import { loadGoogleMaps } from "./maps/loadGoogleMaps";
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
      return;
    }
    requestedGenre = genre;
    bar.setActive(genre.id);
    status.loading(genre);
  });
  const detailEl = byId("detail");

  /** 地図が使えないことを表示し、以降の操作と表示更新を止める（FR-5.3, FR-5.4） */
  let unavailable = false;
  const markMapUnavailable = (message: string, details?: string[]) => {
    if (unavailable) return; // 最初の原因（認証失敗など）を後続のエラーで上書きしない
    unavailable = true;
    app?.disable();
    bar.setActive("");
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

  // 4. Maps JavaScript API を読み込む（FR-5.4）
  let libs: GoogleLibraries;
  try {
    libs = await loadGoogleMaps({
      apiKey: settings.apiKey,
      onAuthFailure: () =>
        markMapUnavailable("Google マップの認証に失敗しました。APIキーとその制限設定を確認してください。"),
    });
  } catch (error) {
    console.error(error);
    markMapUnavailable(error instanceof Error ? error.message : "Google マップを読み込めませんでした。");
    return;
  }
  if (unavailable) return;

  // 5. 地図は1回だけ作り、ジャンルを切り替えても使い続ける（FR-2.3）
  let map: GoogleMap;
  try {
    map = new libs.maps.Map(mapEl, {
      center: config.area.center,
      zoom: config.area.zoom,
      mapId: settings.mapId,
      clickableIcons: false,
    });
  } catch (error) {
    console.error(error);
    markMapUnavailable("地図を作成できませんでした。詳しい原因はブラウザの開発者ツールのコンソールを確認してください。");
    return;
  }

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
    detail: createShopDetail(detailEl, { onClose: () => app?.handleDetailClosed() }),
    setActiveGenre: (id) => bar.setActive(id),
  });

  // 6. 準備中に押されたジャンル、なければ先頭のジャンルから表示する（FR-1.2）
  await app.start(requestedGenre);
}

void main();
