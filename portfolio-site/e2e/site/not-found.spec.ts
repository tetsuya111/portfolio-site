// 存在しないページ・本番に含めないもの
import { expect, test } from "../fixtures";

test("存在しない URL は 404 ページを表示する", async ({ page }) => {
  const res = await page.goto("/no-such-page/");
  expect(res?.status()).toBe(404);
  await expect(page.locator("h1")).toHaveText("ページが見つかりません");
  await page.getByRole("link", { name: "トップページへ戻る" }).click();
  await expect(page).toHaveURL("/");
});

test("存在しないポートフォリオ・記事は 404", async ({ page }) => {
  expect((await page.goto("/portfolios/no-such-portfolio/"))?.status()).toBe(404);
  expect((await page.goto("/articles/no-such-article/"))?.status()).toBe(404);
});

test.describe("本番ビルドに管理画面と保存 API が含まれない", () => {
  for (const path of ["/admin/", "/admin/profile/", "/admin/articles/new/"]) {
    test(`${path} は 404`, async ({ page }) => {
      expect((await page.goto(path))?.status()).toBe(404);
    });
  }

  test("保存 API に送っても保存されない", async ({ request, baseURL }) => {
    const res = await request.put("/__admin/api/profile", {
      headers: { Origin: baseURL!, "Content-Type": "application/json" },
      data: { markdown: "---\nname: x\nrole: y\n---\n" },
    });
    expect(res.status()).not.toBe(200);
    expect(res.headers()["content-type"] ?? "").not.toContain("application/json");
  });
});
