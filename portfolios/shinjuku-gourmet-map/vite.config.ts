import { defineConfig } from "vitest/config";

export default defineConfig({
  // 相対パスで出力し、GitHub Pages などのサブパスにも置けるようにする
  base: "./",
  test: {
    environment: "jsdom",
  },
});
