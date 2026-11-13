// トップページ
import { expect, test } from "../fixtures";
import { formatDisplayDate, loadPortfolios, loadProfile, loadPublishedArticles } from "../content";

const profile = loadProfile();
const portfolios = loadPortfolios();
const latest = loadPublishedArticles().slice(0, 3);

test.beforeEach(async ({ page }) => {
  await page.goto("/");
});

test("氏名・肩書き・一言紹介を表示する", async ({ page }) => {
  await expect(page.locator("h1")).toHaveText(profile.data.name);
  await expect(page.getByText(profile.data.role, { exact: true })).toBeVisible();
  if (profile.data.summary) {
    await expect(page.getByText(profile.data.summary, { exact: true })).toBeVisible();
    await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", profile.data.summary);
  }
});

test("自己紹介ページへのリンクがある", async ({ page }) => {
  await page.getByRole("link", { name: "経歴・自己紹介を見る →" }).click();
  await expect(page).toHaveURL("/about/");
});

test("ポートフォリオを新しい順にタイルで並べる", async ({ page }) => {
  const section = page.locator("section").filter({ has: page.getByRole("heading", { name: "ポートフォリオ", exact: true }) });
  const titles = section.locator("article h3");
  await expect(titles).toHaveText(portfolios.map((p) => p.data.title));
});

test("ポートフォリオ一覧ページへのリンクがある", async ({ page }) => {
  await page.getByRole("link", { name: "ポートフォリオ一覧へ →" }).click();
  await expect(page).toHaveURL("/portfolios/");
});

test("最新の記事を新しい順に最大3件表示する（下書きを除く）", async ({ page }) => {
  const section = page.locator("section").filter({ has: page.getByRole("heading", { name: "最新の記事" }) });
  const items = section.getByRole("listitem");
  await expect(items).toHaveCount(latest.length);
  for (const [i, a] of latest.entries()) {
    await expect(items.nth(i).getByRole("link")).toHaveText(a.data.title);
    await expect(items.nth(i).getByRole("link")).toHaveAttribute("href", `/articles/${a.id}/`);
    await expect(items.nth(i).locator("time")).toHaveText(formatDisplayDate(a.data.date));
  }
});

test("記事一覧ページへのリンクがある", async ({ page }) => {
  await page.getByRole("link", { name: "記事一覧へ →" }).click();
  await expect(page).toHaveURL("/articles/");
});
