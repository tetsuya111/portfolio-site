// ポートフォリオ一覧・タイル・詳細ページ
import { expect, test } from "../fixtures";
import { loadPortfolios } from "../content";

const portfolios = loadPortfolios();

/** タイルの URL ボタンの読み上げ名（見える文字 + 読み上げ用の補足。間の空白はブラウザによって入る） */
const urlButtonName = (title: string) =>
  new RegExp(`^ポートフォリオのURL ↗\\s*（${escapeRegExp(title)}、新しいタブで開く）$`);
const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const withUrl = portfolios.find((p) => p.data.url);

test.describe("一覧ページ /portfolios/", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/portfolios/");
  });

  test("見出しとタイトルが「ポートフォリオ」", async ({ page }) => {
    await expect(page.locator("h1")).toHaveText("ポートフォリオ");
    await expect(page).toHaveTitle("ポートフォリオ | Portfolio");
  });

  test("全件を新しい順にタイルで表示する", async ({ page }) => {
    await expect(page.locator("article h3")).toHaveText(portfolios.map((p) => p.data.title));
  });

  for (const p of portfolios) {
    test(`タイル「${p.data.title}」にタイトルとタグを表示する`, async ({ page }) => {
      const tile = page.locator("article").filter({ has: page.getByRole("heading", { name: p.data.title }) });
      await expect(tile.getByRole("link", { name: p.data.title, exact: true })).toHaveAttribute("href", `/portfolios/${p.id}/`);
      const tags = tile.getByRole("list", { name: "タグ" }).getByRole("listitem");
      await expect(tags).toHaveText(p.data.tags);
    });
  }

  test("URL のあるタイルにだけ「ポートフォリオのURL」ボタンを出す", async ({ page }) => {
    for (const p of portfolios) {
      const tile = page.locator("article").filter({ has: page.getByRole("heading", { name: p.data.title }) });
      const button = tile.getByRole("link", { name: urlButtonName(p.data.title) });
      if (p.data.url) {
        await expect(button).toHaveAttribute("href", p.data.url);
        await expect(button).toHaveAttribute("target", "_blank");
        await expect(button).toHaveAttribute("rel", "noopener noreferrer");
      } else {
        await expect(button).toHaveCount(0);
      }
    }
  });
});

test.describe("タイルの操作", () => {
  const first = portfolios[0]!;

  test("タイトル以外の場所（タイル全体）をクリックしても詳細ページへ移動する", async ({ page }) => {
    await page.goto("/portfolios/");
    const tile = page.locator("article").filter({ has: page.getByRole("heading", { name: first.data.title }) });
    const box = await tile.boundingBox();
    if (!box) throw new Error("タイルが表示されていません");
    // タイルの右下付近（タイトルの文字から離れた場所）をクリックする
    await page.mouse.click(box.x + box.width - 8, box.y + box.height - 8);
    await expect(page).toHaveURL(`/portfolios/${first.id}/`);
  });

  test("URL ボタンは詳細ページへ移動せず、新しいタブで URL を開く", async ({ page, context }) => {
    test.skip(!withUrl, "URL のあるポートフォリオがない");
    await context.route(withUrl!.data.url!, (route) => route.fulfill({ body: "external", contentType: "text/plain" }));
    await page.goto("/portfolios/");
    const tile = page.locator("article").filter({ has: page.getByRole("heading", { name: withUrl!.data.title }) });
    const [popup] = await Promise.all([
      page.waitForEvent("popup"),
      tile.getByRole("link", { name: /^ポートフォリオのURL/ }).click(),
    ]);
    await expect(popup).toHaveURL(withUrl!.data.url!);
    await expect(page).toHaveURL("/portfolios/");
  });

  test("キーボードでタイルのリンクにフォーカスでき、Enter で移動する", async ({ page }) => {
    await page.goto("/portfolios/");
    const link = page.locator("article").first().getByRole("link", { name: first.data.title, exact: true });
    await link.focus();
    await expect(link).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(`/portfolios/${first.id}/`);
  });
});

for (const p of portfolios) {
  test.describe(`詳細ページ /portfolios/${p.id}/`, () => {
    test.beforeEach(async ({ page }) => {
      await page.goto(`/portfolios/${p.id}/`);
    });

    test("タイトル・タグ・URL を表示する", async ({ page }) => {
      await expect(page.locator("h1")).toHaveText(p.data.title);
      await expect(page).toHaveTitle(`${p.data.title} | Portfolio`);
      await expect(page.getByRole("list", { name: "タグ" }).getByRole("listitem")).toHaveText(p.data.tags);
      const urlLink = page.locator("main").getByRole("link", { name: "ポートフォリオのURL ↗", exact: true });
      if (p.data.url) {
        await expect(urlLink).toHaveAttribute("href", p.data.url);
        await expect(urlLink).toHaveAttribute("target", "_blank");
      } else {
        await expect(urlLink).toHaveCount(0);
      }
    });

    test("本文の見出しを表示する", async ({ page }) => {
      for (const m of p.body.matchAll(/^##\s+(.+)$/gm)) {
        await expect(page.locator(".prose h2", { hasText: m[1]!.trim() })).toBeVisible();
      }
    });

    test("「← ポートフォリオ一覧」で一覧ページに戻る", async ({ page }) => {
      await page.getByRole("link", { name: "← ポートフォリオ一覧" }).click();
      await expect(page).toHaveURL("/portfolios/");
    });
  });
}
