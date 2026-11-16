/** Google が公開しているデモ用の Map ID（Advanced Marker の利用に Map ID が必要なため） */
export const DEMO_MAP_ID = "DEMO_MAP_ID";

export interface ApiSettings {
  apiKey: string;
  mapId: string;
}

interface EnvLike {
  VITE_GOOGLE_MAPS_API_KEY?: string;
  VITE_GOOGLE_MAPS_MAP_ID?: string;
}

/**
 * 環境変数（.env）から Google Maps の設定を取り出す。
 * APIキーが未設定なら null を返す。
 */
export function readApiSettings(env: EnvLike): ApiSettings | null {
  const apiKey = env.VITE_GOOGLE_MAPS_API_KEY?.trim() ?? "";
  if (apiKey === "") return null;
  const mapId = env.VITE_GOOGLE_MAPS_MAP_ID?.trim() || DEMO_MAP_ID;
  return { apiKey, mapId };
}
