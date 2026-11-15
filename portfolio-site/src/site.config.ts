import type { ThemeName } from "./lib/theme";

// サイト全体の設定。
// theme は公開ページのデザイン（docs/themes.md）。環境変数 PUBLIC_THEME を指定するとそちらが優先される。
// taskBoxMockUrl はトップページの「タスク百葉箱で相談する」の遷移先の既定値（環境変数 PUBLIC_TASK_BOX_URL が優先）。
// このサイトで配信しているデモを指す。空にすると、環境変数がないときボタンは遷移しない。
export const siteConfig: { name: string; theme: ThemeName; taskBoxMockUrl?: string } = {
  name: "Portfolio",
  theme: "minimal",
  taskBoxMockUrl: "/apps/task-box-it-develop/",
};
