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
});
