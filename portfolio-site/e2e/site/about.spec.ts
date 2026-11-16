// 自己紹介ページ
import { expect, test } from "../fixtures";
import { loadProfile } from "../content";
import { parseProfileBody } from "../../src/lib/profile-body";

const profile = loadProfile();

test.beforeEach(async ({ page }) => {
  await page.goto("/about/");
});

test("氏名と肩書き・一言紹介を表示する", async ({ page }) => {
  await expect(page.locator("h1")).toHaveText(profile.data.name);
  await expect(page.getByText(profile.data.role, { exact: true })).toBeVisible();
  if (profile.data.summary) await expect(page.getByText(profile.data.summary, { exact: true })).toBeVisible();
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
  const headings = [...profile.body.matchAll(/^##\s+(.+?)\s*$/gm)].map((m) => m[1]!.trim());
  expect(headings.length).toBeGreaterThan(0);
  for (const h of headings) {
    await expect(page.locator("main h2", { hasText: h })).toBeVisible();
  }
});

test("経歴をタイムラインで、本文の順に表示する", async ({ page }) => {
  const body = parseProfileBody(profile.body);
  test.skip(!body, "profile.md の本文が決まった書式でないため、Markdown のまま表示する");
  await expect(page.getByRole("list", { name: "経歴" }).locator("[data-period]")).toHaveText(
    (body?.career ?? []).map((c) => c.period),
  );
});
