// 保存 API の防御（astro dev）
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { articleFile, expect, PROFILE_FILE, test, uniqueSlug } from "../fixtures";

const article = (title = "t") => `---\ntitle: ${title}\ndate: 2026-01-01\n---\nx\n`;

test("別サイトの Origin からの保存は 403 で、ファイルを作らない", async ({ request }) => {
  const slug = uniqueSlug("e2e-csrf");
  const res = await request.post("/__admin/api/articles", {
    headers: { Origin: "http://evil.example", "Content-Type": "application/json" },
    data: { slug, markdown: article() },
  });
  expect(res.status()).toBe(403);
  expect(existsSync(articleFile(slug))).toBe(false);
});

test("Origin のない保存は 403", async ({ request }) => {
  const res = await request.put("/__admin/api/profile", {
    headers: { "Content-Type": "application/json" },
    data: { markdown: "---\nname: x\nrole: y\n---\n" },
  });
  expect(res.status()).toBe(403);
});

test("JSON 以外の送信は 415 で、profile.md は変わらない", async ({ request, baseURL }) => {
  const before = await readFile(PROFILE_FILE, "utf8");
  const res = await request.put("/__admin/api/profile", {
    headers: { Origin: baseURL!, "Content-Type": "text/plain" },
    data: JSON.stringify({ markdown: "---\nname: x\nrole: y\n---\n" }),
  });
  expect(res.status()).toBe(415);
  expect(await readFile(PROFILE_FILE, "utf8")).toBe(before);
});

test("1 MB を超える送信は 413", async ({ request, baseURL }) => {
  const res = await request.post("/__admin/api/articles", {
    headers: { Origin: baseURL!, "Content-Type": "application/json" },
    data: JSON.stringify({ slug: "big", markdown: "a".repeat(1_100_000) }),
  });
  expect(res.status()).toBe(413);
});

test("ポートフォリオを追加する API はない（404）", async ({ request, baseURL }) => {
  const res = await request.post("/__admin/api/portfolios", {
    headers: { Origin: baseURL!, "Content-Type": "application/json" },
    data: { slug: "x", markdown: "---\ntitle: x\n---\n" },
  });
  expect(res.status()).toBe(404);
});

test("メソッドが違うと 405", async ({ request }) => {
  expect((await request.get("/__admin/api/profile")).status()).toBe(405);
  expect((await request.get("/__admin/api/articles")).status()).toBe(405);
});
