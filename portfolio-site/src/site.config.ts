import type { ThemeName } from "./lib/theme";

// サイト全体の設定。
// theme は公開ページのデザイン（docs/themes.md）。環境変数 PUBLIC_THEME を指定するとそちらが優先される。
export const siteConfig: { name: string; theme: ThemeName } = {
  name: "Portfolio",
  theme: "minimal",
};
