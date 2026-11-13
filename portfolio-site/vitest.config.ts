import { defineConfig } from "vitest/config";

// 通常のテスト。ビルド成果物を検証するテストは vitest.build.config.ts で別に実行する
export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
    exclude: ["tests/build-output.test.ts"],
  },
});
