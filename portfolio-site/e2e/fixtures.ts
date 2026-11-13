// E2E テスト共通のフィクスチャ
import { rm } from "node:fs/promises";
import { join } from "node:path";
import { test as base, expect } from "@playwright/test";

export const CONTENT_ROOT = join(import.meta.dirname, "..", "src", "content");
export const PROFILE_FILE = join(CONTENT_ROOT, "profile", "profile.md");
export const articleFile = (slug: string) => join(CONTENT_ROOT, "articles", `${slug}.md`);

type Fixtures = {
  /** 外部サイトへの通信を止める（テスト結果を外部の状態に左右させない） */
  blockExternal: void;
  /** テスト中に作った記事ファイルを、テスト後に削除する。作ったスラッグを登録して使う */
  createdArticles: string[];
};

export const test = base.extend<Fixtures>({
  blockExternal: [
    async ({ context }, use) => {
      await context.route(/^https?:\/\/(?!localhost[:/])/, (route) => route.abort("blockedbyclient"));
      await use();
    },
    { auto: true },
  ],
  // Playwright のフィクスチャは第1引数を分割代入で書く必要がある（使う依存がなくても {}）
  // eslint-disable-next-line no-empty-pattern
  createdArticles: async ({}, use) => {
    const slugs: string[] = [];
    await use(slugs);
    await Promise.all(slugs.map((s) => rm(articleFile(s), { force: true })));
  },
});

export { expect };

/** テストごとに重ならないスラッグを作る */
export function uniqueSlug(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}
