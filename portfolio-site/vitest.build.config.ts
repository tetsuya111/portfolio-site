import { defineConfig } from "vitest/config";

// `npm run test:build` 用: astro build 後の dist/ を検証する
export default defineConfig({
  test: { include: ["tests/build-output.test.ts"] },
});
