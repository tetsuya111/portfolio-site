// 管理画面: 自己紹介の編集（astro dev）
import { readFile, writeFile } from "node:fs/promises";
import { expect, PROFILE_FILE, test } from "../fixtures";

// ブラウザのテキスト欄は改行を LF にそろえる（チェックアウト時の CRLF と比べるため）
const toLf = (s: string) => s.replace(/\r\n/g, "\n");

// 各テストのあとで profile.md を元の内容に戻す
let original = "";
test.beforeAll(async () => {
  original = await readFile(PROFILE_FILE, "utf8");
});
test.afterEach(async () => {
  await writeFile(PROFILE_FILE, original, "utf8");
});

test("メニューから各画面へ移動できる", async ({ page }) => {
  await page.goto("/admin/");
  await expect(page.locator("h1")).toHaveText("管理画面");
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex");
  await page.getByRole("link", { name: "自己紹介・経歴を編集する" }).click();
  await expect(page).toHaveURL("/admin/profile/");
  await page.getByRole("link", { name: "記事を追加", exact: true }).click();
  await expect(page).toHaveURL("/admin/articles/new/");
});

test("現在の profile.md の全文を表示する", async ({ page }) => {
  await page.goto("/admin/profile/");
  // テキスト欄は改行を LF にそろえるため、ファイル側もそろえて比べる
  await expect(page.locator("#markdown")).toHaveValue(toLf(await readFile(PROFILE_FILE, "utf8")));
});

test("編集して保存すると profile.md と公開ページが更新される", async ({ page, request }) => {
  const name = `E2E テスト ${Date.now()}`;
  const edited = toLf(original).replace(/^name:.*$/m, `name: ${name}`);

  await page.goto("/admin/profile/");
  await page.locator("#markdown").fill(edited);
  await page.getByRole("button", { name: "保存" }).click();
  await expect(page.getByRole("status")).toHaveText("保存しました。");

  expect(await readFile(PROFILE_FILE, "utf8")).toBe(edited);
  await expect.poll(async () => (await request.get("/about/")).text(), { timeout: 15_000 }).toContain(name);
  // 開発サーバーが画面を再読み込みしても、結果のメッセージが残る
  await page.waitForTimeout(3000);
  await expect(page.getByRole("status")).toHaveText("保存しました。");
});

test("必須項目がないと保存せず、理由を表示する", async ({ page }) => {
  await page.goto("/admin/profile/");
  await page.locator("#markdown").fill(toLf(original).replace(/^name:.*\n/m, ""));
  await page.getByRole("button", { name: "保存" }).click();
  const status = page.getByRole("status");
  await expect(status).toContainText("保存できませんでした（400）");
  await expect(status).toContainText("name");
  expect(await readFile(PROFILE_FILE, "utf8")).toBe(original);
});

test("frontmatter がないと保存しない", async ({ page }) => {
  await page.goto("/admin/profile/");
  await page.locator("#markdown").fill("# frontmatter なし");
  await page.getByRole("button", { name: "保存" }).click();
  await expect(page.getByRole("status")).toContainText("frontmatter");
  expect(await readFile(PROFILE_FILE, "utf8")).toBe(original);
});

test("通信に失敗したときはその旨を表示する", async ({ page }) => {
  await page.route("**/__admin/api/profile", (route) => route.abort("failed"));
  await page.goto("/admin/profile/");
  await page.getByRole("button", { name: "保存" }).click();
  await expect(page.getByRole("status")).toContainText("送信できませんでした");
});
