import { defineConfig, devices } from "@playwright/test";

// E2E テスト（npm run test:e2e）
// - site: 本番と同じ静的ビルド（astro build → astro preview）に対して公開ページを検証する
// - admin: 管理画面は開発サーバー（astro dev）でしか動かないため、dev サーバーに対して検証する。
//   実際の src/content/ を書き換えるので、1件ずつ順番に実行し、テストごとに元へ戻す（e2e/fixtures.ts）
const SITE_PORT = 4322;
const DEV_PORT = 4399;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // 並列数が多いと astro preview の応答とブラウザ起動が追いつかず、ページ読み込みがタイムアウトする
  workers: 3,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    ...devices["Desktop Chrome"],
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "site",
      testDir: "./e2e/site",
      use: { baseURL: `http://localhost:${SITE_PORT}` },
    },
    {
      name: "admin",
      testDir: "./e2e/admin",
      fullyParallel: false,
      workers: 1,
      use: { baseURL: `http://localhost:${DEV_PORT}` },
    },
  ],
  webServer: [
    {
      command: `npm run build && npx astro preview --port ${SITE_PORT}`,
      url: `http://localhost:${SITE_PORT}/`,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
    {
      command: `npx astro dev --port ${DEV_PORT}`,
      url: `http://localhost:${DEV_PORT}/admin/`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
