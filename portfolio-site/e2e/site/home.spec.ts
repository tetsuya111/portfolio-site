// トップページ
import type { Locator, Page } from "@playwright/test";
import { expect, test } from "../fixtures";
import {
  formatDisplayDate,
  loadPortfolios,
  loadProfile,
  loadPublishedArticles,
  loadPublishedItArticles,
  loadServices,
  loadSkills,
} from "../content";

const profile = loadProfile();
const portfolios = loadPortfolios().slice(0, 6);
const latest = loadPublishedArticles().slice(0, 3);
const latestIt = loadPublishedItArticles().slice(0, 3);
const services = loadServices();
const skills = loadSkills();

/** 見出し（h2）の名前でトップページのセクションを取り出す */
const section = (page: Page, name: string): Locator =>
  page.locator("main > section").filter({ has: page.getByRole("heading", { level: 2, name, exact: true }) });

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

test("冒頭に得意分野としてスキルの先頭6件を表示する", async ({ page }) => {
  const items = page.getByRole("list", { name: "得意分野" }).getByRole("listitem");
  await expect(items).toHaveText(skills.slice(0, 6).map((s) => s.data.name));
});

test("自己紹介ページへのリンクがある", async ({ page }) => {
  await page.getByRole("link", { name: "経歴・自己紹介を見る →" }).click();
  await expect(page).toHaveURL("/about/");
});

test.describe("相談ボタン", () => {
  test("「ご相談はこちら」と大きなボタン2つをファーストビューに表示する", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await expect(page.getByRole("heading", { name: "ご相談はこちら" })).toBeInViewport();
    for (const b of [
      page.getByRole("button", { name: "フォームで相談する" }),
      page.getByRole("link", { name: /^タスク百葉箱で相談する/ }),
    ]) {
      await expect(b).toBeInViewport();
      const { height, fontSize } = await b.evaluate((el) => ({
        height: el.getBoundingClientRect().height,
        fontSize: parseFloat(getComputedStyle(el).fontSize),
      }));
      expect(height).toBeGreaterThanOrEqual(56);
      expect(fontSize).toBeGreaterThanOrEqual(18);
    }
  });

  test("タスク百葉箱のボタンはモックの URL（デモ）へ移動する", async ({ page }) => {
    await expect(page.getByRole("link", { name: /^タスク百葉箱で相談する/ })).toHaveAttribute(
      "href",
      "/apps/task-box-it-develop/",
    );
  });

  test("フォームをダイアログで開き、入力内容から mailto のリンクを作る", async ({ page }) => {
    await page.getByRole("button", { name: "フォームで相談する" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByLabel("お名前").fill("山田 太郎");
    await dialog.getByLabel("返信先メールアドレス").fill("taro@example.com");
    await dialog.getByLabel("ご相談内容").fill("ツールを作ってほしい & 相談したい");
    // ヘッドレスのブラウザでは mailto: を開いても何も起きないため、作ったリンクをダイアログの属性で確かめる
    await dialog.getByRole("button", { name: "メールソフトで送信する" }).click();
    const mailto = await page.locator("dialog").getAttribute("data-last-mailto");
    expect(mailto).toMatch(/^mailto:contact@example\.com\?subject=/);
    expect(decodeURIComponent(mailto ?? "")).toContain("ツールを作ってほしい & 相談したい");
    expect(decodeURIComponent(mailto ?? "")).toContain("返信先メールアドレス: taro@example.com");
  });

  test("必須項目が空なら送信せず、Esc でダイアログを閉じる", async ({ page }) => {
    await page.getByRole("button", { name: "フォームで相談する" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: "メールソフトで送信する" }).click();
    await expect(page.locator("dialog")).not.toHaveAttribute("data-last-mailto", /.*/);
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });
});

test("セクションをサービス・ポートフォリオ・スキル・最新の記事・IT ニュースの順に並べる", async ({ page }) => {
  await expect(page.locator("main > section:not(:first-child) > div > h2")).toHaveText([
    "サービス",
    "ポートフォリオ",
    "スキル",
    "最新の記事",
    "IT ニュース",
  ]);
});

test("サービスを順にタイルで表示し、注記を添える", async ({ page }) => {
  const s = section(page, "サービス");
  await expect(s.locator("h3")).toHaveText(services.map((x) => x.data.title));
  for (const x of services) await expect(s.getByText(x.data.description, { exact: true })).toBeVisible();
  await expect(s.getByText("※このサービスは一例です。相談していただければなんでも対応します。")).toBeVisible();
});

test("スキルを順にタイルで表示し、解説・作れるもの・使われている例を載せる", async ({ page }) => {
  const s = section(page, "スキル");
  await expect(s.locator("h3")).toHaveText(skills.map((x) => x.data.name));
  for (const x of skills) {
    const tile = s.locator("article").filter({ has: page.getByRole("heading", { name: x.data.name, exact: true }) });
    await expect(tile.getByText(x.data.description, { exact: true })).toBeVisible();
    await expect(tile.getByRole("list", { name: "作れるもの" }).getByRole("listitem")).toHaveText(x.data.examples);
    await expect(tile.getByRole("list", { name: "使われている例" }).getByRole("listitem")).toHaveText(x.data.famous);
  }
});

test("ポートフォリオを新しい順に最大6件、概要つきのタイルで並べる", async ({ page }) => {
  const s = section(page, "ポートフォリオ");
  await expect(s.locator("article h3")).toHaveText(portfolios.map((p) => p.data.title));
  for (const p of portfolios) {
    if (p.data.description) await expect(s.getByText(p.data.description, { exact: true })).toBeVisible();
  }
});

test("ポートフォリオ一覧ページへのリンクがある", async ({ page }) => {
  await page.getByRole("link", { name: "ポートフォリオ一覧へ →" }).click();
  await expect(page).toHaveURL("/portfolios/");
});

test("最新の記事を新しい順に最大3件、説明とタグつきで表示する（下書きを除く）", async ({ page }) => {
  const s = section(page, "最新の記事");
  const titles = s.getByRole("heading", { level: 3 });
  await expect(titles).toHaveText(latest.map((a) => a.data.title));
  for (const [i, a] of latest.entries()) {
    await expect(titles.nth(i).getByRole("link")).toHaveAttribute("href", `/articles/${a.id}/`);
    await expect(s.locator("time").nth(i)).toHaveText(formatDisplayDate(a.data.date));
    if (a.data.description) await expect(s.getByText(a.data.description, { exact: true })).toBeVisible();
  }
});

test("記事一覧ページへのリンクがある", async ({ page }) => {
  await page.getByRole("link", { name: "記事一覧へ →" }).click();
  await expect(page).toHaveURL("/articles/");
});

test("IT ニュースの最新3件と一覧へのリンクを表示する", async ({ page }) => {
  const s = section(page, "IT ニュース");
  if (latestIt.length === 0) {
    await expect(s.getByText("まだありません。")).toBeVisible();
  } else {
    await expect(s.getByRole("heading", { level: 3 })).toHaveText(latestIt.map((a) => a.data.title));
  }
  await s.getByRole("link", { name: "IT ニュース一覧へ →" }).click();
  await expect(page).toHaveURL("/it-news/");
});
