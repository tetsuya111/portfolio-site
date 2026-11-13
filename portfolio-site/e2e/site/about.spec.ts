// 自己紹介ページ
import { expect, test } from "../fixtures";
import { loadProfile } from "../content";

const profile = loadProfile();

test.beforeEach(async ({ page }) => {
  await page.goto("/about/");
});

test("氏名と肩書きを表示する", async ({ page }) => {
  await expect(page.locator("h1")).toHaveText(profile.data.name);
  await expect(page.getByText(profile.data.role, { exact: true })).toBeVisible();
  await expect(page).toHaveTitle("自己紹介 | Portfolio");
});

test("リンクを別タブで開く設定で表示する", async ({ page }) => {
  for (const link of profile.data.links ?? []) {
    const a = page.locator("main").getByRole("link", { name: link.label, exact: true });
    await expect(a).toHaveAttribute("href", link.url);
    await expect(a).toHaveAttribute("target", "_blank");
    await expect(a).toHaveAttribute("rel", /noopener/);
  }
});

test("本文の見出しを表示する", async ({ page }) => {
  const headings = [...profile.body.matchAll(/^##\s+(.+)$/gm)].map((m) => m[1]!.trim());
  expect(headings.length).toBeGreaterThan(0);
  for (const h of headings) {
    await expect(page.locator(".prose h2", { hasText: h })).toBeVisible();
  }
});
