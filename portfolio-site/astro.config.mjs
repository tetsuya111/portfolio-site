// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import { localAdmin } from "./integrations/local-admin.ts";

// https://docs.astro.build/en/reference/configuration-reference/
export default defineConfig({
  output: "static",
  trailingSlash: "always",
  // 管理画面と保存 API は astro dev のときだけ有効（本番ビルドには含まれない）
  integrations: [localAdmin({ contentRoot: "./src/content" })],
  vite: { plugins: [tailwindcss()] },
  // 本文のコードブロックの配色。既定の github-dark はコメントの文字が背景とのコントラスト 3:1 程度で
  // WCAG 2.1 AA（4.5:1）を満たさないため、コメントも十分なコントラストがある github-dark-default を使う
  markdown: { shikiConfig: { theme: "github-dark-default" } },
});
