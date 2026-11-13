// 記事一覧・詳細ページ
import { expect, test } from "../fixtures";
import { formatDisplayDate, loadDraftArticles, loadPublishedArticles } from "../content";

const articles = loadPublishedArticles();
const drafts = loadDraftArticles();

test.describe("一覧ページ /articles/", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/articles/");
  });

  test("公開記事を新しい順に表示する", async ({ page }) => {
    await expect(page.locator("h1")).toHaveText("記事");
    await expect(page.locator("main li h2")).toHaveText(articles.map((a) => a.data.title));
  });

  test("各記事の日付・説明・タグとリンクを表示する", async ({ page }) => {
    const items = page.locator("main > ul > li");
    for (const [i, a] of articles.entries()) {
      const item = items.nth(i);
      await expect(item.locator("time")).toHaveText(formatDisplayDate(a.data.date));
      await expect(item.getByRole("link", { name: a.data.title })).toHaveAttribute("href", `/articles/${a.id}/`);
      if (a.data.description) await expect(item).toContainText(a.data.description);
      if (a.data.tags.length > 0) {
        await expect(item.getByRole("list", { name: "タグ" }).getByRole("listitem")).toHaveText(a.data.tags);
      }
    }
  });

  test("下書きの記事を表示しない", async ({ page }) => {
    for (const d of drafts) {
      await expect(page.getByText(d.data.title)).toHaveCount(0);
    }
  });

  test("記事のタイトルをクリックすると詳細ページへ移動する", async ({ page }) => {
    const first = articles[0]!;
    await page.getByRole("link", { name: first.data.title }).click();
    await expect(page).toHaveURL(`/articles/${first.id}/`);
  });
});

for (const a of articles) {
  test.describe(`詳細ページ /articles/${a.id}/`, () => {
    test.beforeEach(async ({ page }) => {
      await page.goto(`/articles/${a.id}/`);
    });

    test("タイトル・日付・タグ・説明を表示する", async ({ page }) => {
      await expect(page.locator("h1")).toHaveText(a.data.title);
      await expect(page).toHaveTitle(`${a.data.title} | Portfolio`);
      await expect(page.locator("main time")).toHaveText(formatDisplayDate(a.data.date));
      if (a.data.tags.length > 0) {
        await expect(page.getByRole("list", { name: "タグ" }).getByRole("listitem")).toHaveText(a.data.tags);
      }
      if (a.data.description) {
        await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", a.data.description);
      }
    });

    test("本文の見出しを表示する", async ({ page }) => {
      for (const m of a.body.matchAll(/^##\s+(.+)$/gm)) {
        await expect(page.locator("article.prose h2", { hasText: m[1]!.trim() })).toBeVisible();
      }
    });

    test("本文の画像はすべて代替テキストを持つ", async ({ page }) => {
      const images = page.locator("article.prose img");
      for (const img of await images.all()) {
        await expect(img).toHaveAttribute("alt", /\S/);
      }
    });

    test("「← 記事一覧」で一覧ページに戻る", async ({ page }) => {
      await page.getByRole("link", { name: "← 記事一覧" }).click();
      await expect(page).toHaveURL("/articles/");
    });
  });
}

for (const d of drafts) {
  test(`下書きの記事 /articles/${d.id}/ はページがない（404）`, async ({ page }) => {
    const res = await page.goto(`/articles/${d.id}/`);
    expect(res?.status()).toBe(404);
  });
}
