import type { GoogleLibraries } from "./googleTypes";

export const SCRIPT_ID = "google-maps-js";
export const CALLBACK_NAME = "__shinjukuGourmetMapInit";
/** この時間内に読み込みが終わらなければ失敗とみなす（通信の停止・ブロック対策） */
export const LOAD_TIMEOUT_MS = 15_000;

const SCRIPT_URL = "https://maps.googleapis.com/maps/api/js";

export interface LoadOptions {
  apiKey: string;
  /** APIキーが無効・制限違反などで Google が認証に失敗したときに呼ばれる */
  onAuthFailure?: () => void;
}

interface GoogleGlobal {
  google?: { maps: { importLibrary(name: string): Promise<unknown> } };
  gm_authFailure?: () => void;
  [CALLBACK_NAME]?: () => void;
}

/** Maps JavaScript API を読み込み、このアプリが使うライブラリを返す（ページで1回だけ呼ぶ） */
export async function loadGoogleMaps({ apiKey, onAuthFailure }: LoadOptions): Promise<GoogleLibraries> {
  const global = window as unknown as GoogleGlobal;
  if (onAuthFailure) global.gm_authFailure = onAuthFailure;

  await new Promise<void>((resolve, reject) => {
    const fail = (message: string) => {
      clearTimeout(timer);
      reject(new Error(message));
    };
    const timer = setTimeout(
      () => fail("Google マップを時間内に読み込めませんでした。通信状況や広告ブロッカーの設定を確認してください。"),
      LOAD_TIMEOUT_MS,
    );
    global[CALLBACK_NAME] = () => {
      clearTimeout(timer);
      resolve();
    };

    const url = new URL(SCRIPT_URL);
    url.search = new URLSearchParams({
      key: apiKey,
      v: "weekly",
      loading: "async",
      language: "ja",
      region: "JP",
      callback: CALLBACK_NAME,
    }).toString();

    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.src = url.toString();
    script.async = true;
    script.addEventListener("error", () =>
      fail("Google マップを読み込めませんでした。通信状況を確認してください。"),
    );
    document.head.append(script);
  });

  const maps = global.google?.maps;
  if (!maps) throw new Error("Google マップを読み込めませんでした。");
  const [core, mapsLib, marker, places] = await Promise.all(
    ["core", "maps", "marker", "places"].map((name) => maps.importLibrary(name)),
  );
  return { core, maps: mapsLib, marker, places } as GoogleLibraries;
}
