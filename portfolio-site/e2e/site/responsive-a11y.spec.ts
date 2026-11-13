// 画面幅ごとの表示と、アクセシビリティ（axe-core）
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "../fixtures";
import { allPublicPaths } from "../content";

const VIEWPORTS = [
  { name: "スマートフォン", width: 375, height: 812, columns: 1 },
  { name: "タブレット", width: 768, height: 1024, columns: 2 },
  { name: "デスクトップ", width: 1280, height: 800, columns: 3 },
];

for (const vp of VIEWPORTS) {
  test.describe(`${vp.name}（幅 ${vp.width}px）`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    for (const path of [...allPublicPaths(), "/no-such-page/"]) {
      test(`${path} に横スクロールが出ない`, async ({ page }) => {
        await page.goto(path);
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow).toBeLessThanOrEqual(0);
      });
    }

    test(`ポートフォリオのタイルを ${vp.columns} 列で並べる`, async ({ page }) => {
      await page.goto("/portfolios/");
      const columns = await page
        .locator("main .grid")
        .evaluate((el) => getComputedStyle(el).gridTemplateColumns.split(" ").filter(Boolean).length);
      expect(columns).toBe(vp.columns);
    });
  });
}

test.describe("アクセシビリティ（WCAG 2.1 A/AA）", () => {
  for (const path of [...allPublicPaths(), "/no-such-page/"]) {
    test(`${path} に違反がない`, async ({ page }) => {
      await page.goto(path);
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      const summary = results.violations.map((v) => `${v.id}: ${v.help}（${v.nodes.length}件）`);
      expect(summary).toEqual([]);
    });
  }
});

test("Tab キーでヘッダーのリンクを順に移動できる", async ({ page }) => {
  await page.goto("/");
  const expected = ["Portfolio", "ホーム", "自己紹介", "ポートフォリオ", "記事"];
  for (const name of expected) {
    await page.keyboard.press("Tab");
    await expect(page.locator(":focus")).toHaveText(name);
  }
});
