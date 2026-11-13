// 全公開ページに共通するレイアウト・ナビゲーション
import { expect, test } from "../fixtures";
import { allPublicPaths } from "../content";

const NAV = [
  { label: "ホーム", path: "/" },
  { label: "自己紹介", path: "/about/" },
  { label: "ポートフォリオ", path: "/portfolios/" },
  { label: "記事", path: "/articles/" },
];

for (const path of allPublicPaths()) {
  test.describe(`共通レイアウト ${path}`, () => {
    test("200 で表示され、lang・タイトル・見出しが正しい", async ({ page }) => {
      const res = await page.goto(path);
      expect(res?.status()).toBe(200);
      await expect(page.locator("html")).toHaveAttribute("lang", "ja");
      await expect(page).toHaveTitle(/Portfolio$/);
      await expect(page.locator("h1")).toHaveCount(1);
    });

    test("ヘッダーのナビゲーションとフッターがある", async ({ page }) => {
      await page.goto(path);
      const nav = page.getByRole("navigation");
      await expect(nav.getByRole("link", { name: "Portfolio", exact: true })).toHaveAttribute("href", "/");
      for (const { label, path: href } of NAV) {
        await expect(nav.getByRole("link", { name: label, exact: true })).toHaveAttribute("href", href);
      }
      await expect(page.getByRole("contentinfo")).toContainText("Portfolio");
    });
  });
}

test.describe("ナビゲーションで移動できる", () => {
  for (const { label, path } of NAV) {
    test(`「${label}」→ ${path}`, async ({ page }) => {
      await page.goto("/articles/");
      await page.getByRole("navigation").getByRole("link", { name: label, exact: true }).click();
      await expect(page).toHaveURL(path);
      await expect(page.locator("h1")).toBeVisible();
    });
  }

  test("サイト名のリンクでトップに戻る", async ({ page }) => {
    await page.goto("/about/");
    await page.getByRole("navigation").getByRole("link", { name: "Portfolio", exact: true }).click();
    await expect(page).toHaveURL("/");
  });
});
