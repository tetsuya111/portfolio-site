import type { GoogleLibraries } from "./googleTypes";

export const SCRIPT_ID = "google-maps-js";
export const CALLBACK_NAME = "__shinjukuGourmetMapInit";

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

/**
 * Maps JavaScript API を読み込む関数を作る。
 * 返した関数は読み込み中・読み込み済みなら同じ Promise を返し、script を重複して追加しない。
 * 読み込みに失敗した場合は保持せず、次の呼び出しで読み込み直す。
 */
export function createGoogleMapsLoader(): (options: LoadOptions) => Promise<GoogleLibraries> {
  let loading: Promise<GoogleLibraries> | null = null;

  return (options) => {
    loading ??= load(options).catch((error: unknown) => {
      loading = null;
      throw error;
    });
    return loading;
  };
}

function load({ apiKey, onAuthFailure }: LoadOptions): Promise<GoogleLibraries> {
  const global = window as unknown as GoogleGlobal;
  if (onAuthFailure) global.gm_authFailure = onAuthFailure;

  const ready = new Promise<void>((resolve, reject) => {
    global[CALLBACK_NAME] = () => resolve();

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
    script.addEventListener("error", () => {
      script.remove();
      reject(new Error("Google マップを読み込めませんでした。通信状況を確認してください。"));
    });
    document.head.append(script);
  });

  return ready.then(async () => {
    const maps = global.google?.maps;
    if (!maps) throw new Error("Google マップを読み込めませんでした。");
    const [core, mapsLib, marker, places] = await Promise.all(
      ["core", "maps", "marker", "places"].map((name) => maps.importLibrary(name)),
    );
    return { core, maps: mapsLib, marker, places } as GoogleLibraries;
  });
}
