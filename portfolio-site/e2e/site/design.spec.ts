// デザインの見た目の強弱とフォーカス表示（issue #6）
import { expect, test } from "../fixtures";

const fontSize = (el: Element) => parseFloat(getComputedStyle(el).fontSize);

test("トップページで氏名をもっとも大きな文字で表示する", async ({ page }) => {
  await page.goto("/");
  const h1Size = await page.locator("h1").evaluate(fontSize);
  const otherSizes = await page.locator("main :is(h2, h3, p, a, li)").evaluateAll((els) =>
    els.map((el) => parseFloat(getComputedStyle(el).fontSize)),
  );
  expect(otherSizes.length).toBeGreaterThan(0);
  for (const size of otherSizes) expect(h1Size).toBeGreaterThan(size);
});

test.describe("ポートフォリオのタイル", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/portfolios/");
  });

  test("タイトルをタグより大きな文字で表示する", async ({ page }) => {
    const tile = page.locator("main article").first();
    const titleSize = await tile.locator("h3").evaluate(fontSize);
    const tagSize = await tile.getByRole("list", { name: "タグ" }).getByRole("listitem").first().evaluate(fontSize);
    expect(titleSize).toBeGreaterThan(tagSize);
  });

  test("URL ボタンをタイルの背景と違う色で塗りつぶす", async ({ page }) => {
    const tile = page.locator("main article").filter({ has: page.locator('a[target="_blank"]') }).first();
    const tileBg = await tile.evaluate((el) => getComputedStyle(el).backgroundColor);
    const buttonBg = await tile.locator('a[target="_blank"]').evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(buttonBg).not.toBe("rgba(0, 0, 0, 0)");
    expect(buttonBg).not.toBe(tileBg);
  });

  test("タイトルにフォーカスするとタイル全体に枠を表示する", async ({ page }) => {
    const tile = page.locator("main article").first();
    await tile.locator("h3 a").focus();
    const shadow = await tile.evaluate((el) => getComputedStyle(el).boxShadow);
    expect(shadow).not.toBe("none");
  });
});

test("キーボードでフォーカスしたリンクに枠線を表示する", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const outline = await page.locator(":focus").evaluate((el) => {
    const s = getComputedStyle(el);
    return { style: s.outlineStyle, width: parseFloat(s.outlineWidth) };
  });
  expect(outline.style).not.toBe("none");
  expect(outline.width).toBeGreaterThanOrEqual(2);
});
