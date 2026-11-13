// 管理画面: 記事の追加（astro dev）
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parseMarkdown } from "../../src/lib/markdown-file";
import { articleFile, expect, test, uniqueSlug } from "../fixtures";

test.beforeEach(async ({ page }) => {
  await page.goto("/admin/articles/new/");
});

const form = (page: import("@playwright/test").Page) => page.locator("#article-form");
const upload = (page: import("@playwright/test").Page) => page.locator("#upload-form");

test.describe("フォームで入力", () => {
  test("保存すると md が作られ、記事ページに表示される", async ({ page, context, request, createdArticles }) => {
    const slug = uniqueSlug("e2e-form");
    createdArticles.push(slug);
    const title = 'E2E: "引用" と # を含むタイトル';
    const f = form(page);
    await f.getByLabel(/スラッグ/).fill(slug);
    await f.getByLabel("タイトル").fill(title);
    await f.getByLabel("日付").fill("2026-01-02");
    await f.getByLabel(/タグ/).fill("E2E, テスト ,");
    await f.getByLabel(/説明/).fill("E2E テストで作成");
    await f.getByLabel(/本文/).fill("## 見出し\n\n本文です。");
    await f.getByRole("button", { name: "保存" }).click();

    await expect(page.getByRole("status")).toHaveText(`保存しました: /articles/${slug}/`);
    // 保存後はフォームを空に戻す
    await expect(f.getByLabel("タイトル")).toHaveValue("");

    const { data, body } = parseMarkdown(await readFile(articleFile(slug), "utf8"));
    expect(data).toEqual({
      title,
      date: "2026-01-02",
      tags: ["E2E", "テスト"],
      description: "E2E テストで作成",
    });
    expect(body).toContain("## 見出し");

    await expect.poll(async () => (await request.get(`/articles/${slug}/`)).status(), { timeout: 15_000 }).toBe(200);
    // 管理画面は保存後に開発サーバーが再読み込みすることがあるため、記事は別のタブで開く
    const view = await context.newPage();
    await view.goto(`/articles/${slug}/`);
    await expect(view.locator("h1")).toHaveText(title);
    await expect(view.locator("article.prose h2")).toHaveText("見出し");
  });

  test("保存後に開発サーバーが画面を再読み込みしても、結果のメッセージが残る", async ({ page, createdArticles }) => {
    const slug = uniqueSlug("e2e-flash");
    createdArticles.push(slug);
    const f = form(page);
    await f.getByLabel(/スラッグ/).fill(slug);
    await f.getByLabel("タイトル").fill("flash");
    await f.getByLabel(/本文/).fill("x");
    await f.getByRole("button", { name: "保存" }).click();
    await expect(page.getByRole("status")).toHaveText(`保存しました: /articles/${slug}/`);
    // ファイルの変更を検知した再読み込みが起きるのを待つ
    await page.waitForTimeout(4000);
    await expect(page.getByRole("status")).toHaveText(`保存しました: /articles/${slug}/`);
  });

  test("下書きで保存すると、公開されない旨を表示し一覧にも出ない", async ({ page, request, createdArticles }) => {
    const slug = uniqueSlug("e2e-draft");
    createdArticles.push(slug);
    const f = form(page);
    await f.getByLabel(/スラッグ/).fill(slug);
    await f.getByLabel("タイトル").fill(`下書き ${slug}`);
    await f.getByLabel(/下書き/).check();
    await f.getByLabel(/本文/).fill("下書き本文");
    await f.getByRole("button", { name: "保存" }).click();

    await expect(page.getByRole("status")).toContainText("下書きとして保存しました");
    expect(parseMarkdown(await readFile(articleFile(slug), "utf8")).data.draft).toBe(true);
    // ファイルの変更が反映されるのを待ってから、一覧に出ないことを確かめる
    await page.waitForTimeout(1500);
    expect(await (await request.get("/articles/")).text()).not.toContain(slug);
  });

  test("同じスラッグでは保存せず、既存ファイルを上書きしない", async ({ page, createdArticles }) => {
    const slug = uniqueSlug("e2e-dup");
    createdArticles.push(slug);
    const f = form(page);
    for (const title of ["1回目", "2回目"]) {
      await f.getByLabel(/スラッグ/).fill(slug);
      await f.getByLabel("タイトル").fill(title);
      await f.getByLabel(/本文/).fill(title);
      await f.getByRole("button", { name: "保存" }).click();
      await expect(page.getByRole("status")).not.toHaveText("");
    }
    await expect(page.getByRole("status")).toContainText("保存できませんでした（409）");
    expect(parseMarkdown(await readFile(articleFile(slug), "utf8")).data.title).toBe("1回目");
  });

  test("スラッグの形式が不正だとブラウザが送信を止める", async ({ page }) => {
    const f = form(page);
    await f.getByLabel(/スラッグ/).fill("Bad Slug");
    await f.getByLabel("タイトル").fill("x");
    await f.getByLabel(/本文/).fill("x");
    let sent = false;
    await page.route("**/__admin/api/articles", (route) => {
      sent = true;
      return route.continue();
    });
    await f.getByRole("button", { name: "保存" }).click();
    expect(await f.getByLabel(/スラッグ/).evaluate((el: HTMLInputElement) => el.validity.patternMismatch)).toBe(true);
    expect(sent).toBe(false);
  });

  test("必須項目が空だとブラウザが送信を止める", async ({ page }) => {
    let sent = false;
    await page.route("**/__admin/api/articles", (route) => {
      sent = true;
      return route.continue();
    });
    await form(page).getByRole("button", { name: "保存" }).click();
    expect(await form(page).getByLabel(/スラッグ/).evaluate((el: HTMLInputElement) => el.validity.valueMissing)).toBe(true);
    expect(sent).toBe(false);
  });

  test("API が拒否したスラッグ（パス区切りなど）はファイルを作らない", async ({ page }) => {
    // ブラウザ側の検査を外して、サーバー側の検査を確かめる
    await form(page).getByLabel(/スラッグ/).evaluate((el: HTMLInputElement) => el.removeAttribute("pattern"));
    const f = form(page);
    await f.getByLabel(/スラッグ/).fill("../evil");
    await f.getByLabel("タイトル").fill("x");
    await f.getByLabel(/本文/).fill("x");
    await f.getByRole("button", { name: "保存" }).click();
    await expect(page.getByRole("status")).toContainText("保存できませんでした（400）");
    expect(existsSync(join(articleFile("x"), "..", "..", "evil.md"))).toBe(false);
  });
});

test.describe("md ファイルをアップロード", () => {
  async function mdFile(name: string, content: string): Promise<string> {
    const dir = await mkdtemp(join(tmpdir(), "e2e-upload-"));
    const path = join(dir, name);
    await writeFile(path, content, "utf8");
    return path;
  }

  test("スラッグが空ならファイル名をスラッグにして保存する", async ({ page, createdArticles }) => {
    const slug = uniqueSlug("e2e-upload");
    createdArticles.push(slug);
    const content = `---\ntitle: アップロード ${slug}\ndate: 2026-02-03\n---\n\n本文\n`;
    await upload(page).getByLabel(/md ファイル/).setInputFiles(await mdFile(`${slug}.md`, content));
    await upload(page).getByRole("button", { name: "アップロードして保存" }).click();
    await expect(page.getByRole("status")).toHaveText(`保存しました: /articles/${slug}/`);
    expect(await readFile(articleFile(slug), "utf8")).toBe(content);
  });

  test("スラッグを指定するとその名前で保存する", async ({ page, createdArticles }) => {
    const slug = uniqueSlug("e2e-named");
    createdArticles.push(slug);
    await upload(page).getByLabel(/スラッグ/).fill(slug);
    await upload(page)
      .getByLabel(/md ファイル/)
      .setInputFiles(await mdFile("Some File.md", "---\ntitle: t\ndate: 2026-02-03\n---\nx\n"));
    await upload(page).getByRole("button", { name: "アップロードして保存" }).click();
    await expect(page.getByRole("status")).toHaveText(`保存しました: /articles/${slug}/`);
    expect(existsSync(articleFile(slug))).toBe(true);
  });

  test("frontmatter に date がない md は保存しない", async ({ page }) => {
    const slug = uniqueSlug("e2e-nodate");
    await upload(page).getByLabel(/md ファイル/).setInputFiles(await mdFile(`${slug}.md`, "---\ntitle: t\n---\nx\n"));
    await upload(page).getByRole("button", { name: "アップロードして保存" }).click();
    await expect(page.getByRole("status")).toContainText("保存できませんでした（400）");
    await expect(page.getByRole("status")).toContainText("date");
    expect(existsSync(articleFile(slug))).toBe(false);
  });

  test("下書きの md は公開されない旨を表示する", async ({ page, createdArticles }) => {
    const slug = uniqueSlug("e2e-updraft");
    createdArticles.push(slug);
    await upload(page)
      .getByLabel(/md ファイル/)
      .setInputFiles(await mdFile(`${slug}.md`, "---\ntitle: t\ndate: 2026-02-03\ndraft: true\n---\nx\n"));
    await upload(page).getByRole("button", { name: "アップロードして保存" }).click();
    await expect(page.getByRole("status")).toContainText("下書きとして保存しました");
  });
});
