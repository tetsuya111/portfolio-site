// 公開ページのデザインテーマ。テーマごとの色・書体は src/styles/global.css の
// [data-theme="<名前>"] に定義する（追加方法は docs/themes.md）。
export const THEMES = ["minimal", "campus"] as const;
export type ThemeName = (typeof THEMES)[number];
export const DEFAULT_THEME: ThemeName = "minimal";

const isThemeName = (v: string): v is ThemeName => (THEMES as readonly string[]).includes(v);

/**
 * ビルドに使うテーマ名を決める。環境変数（PUBLIC_THEME）→ 設定ファイル（site.config.ts）の順に、
 * 空でない最初の値を使う。どちらも空なら既定のテーマ。
 * 存在しない名前は誤記のまま公開しないよう、エラーにしてビルドを止める。
 */
export function resolveTheme(envValue?: string, configValue?: string): ThemeName {
  const value = [envValue, configValue].map((v) => v?.trim() ?? "").find((v) => v !== "");
  if (value === undefined) return DEFAULT_THEME;
  if (!isThemeName(value)) {
    throw new Error(`テーマ "${value}" はありません。使えるテーマ: ${THEMES.join(", ")}`);
  }
  return value;
}
