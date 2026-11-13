// md ファイルの書き込み。管理画面の保存 API とポートフォリオ追加コマンドから使う。
// どの関数も、検証を通過するまでファイルに触れない。
import { mkdir, rename, rm, writeFile } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { join } from "node:path";
import type { z } from "astro/zod";
import { ContentConflictError, ContentValidationError } from "./errors";
import { parseMarkdown, stringifyMarkdown } from "./markdown-file";
import { articleSchema, formatIssues, portfolioSchema, profileSchema } from "./schemas";
import { assertValidSlug } from "./slug";

export const PROFILE_PATH = ["profile", "profile.md"] as const;

function validateFrontmatter(markdown: string, schema: z.ZodType): void {
  const { data } = parseMarkdown(markdown);
  const result = schema.safeParse(data);
  if (!result.success) throw new ContentValidationError(formatIssues(result.error));
}

/** 新規ファイルとして書く。既にあれば ContentConflictError（確認と作成の間の競合も起きない）。 */
async function writeNew(path: string, data: string): Promise<void> {
  try {
    await writeFile(path, data, { encoding: "utf8", flag: "wx" });
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "EEXIST") {
      throw new ContentConflictError(`同じスラッグのファイルが既にあります: ${path}`);
    }
    throw e;
  }
}

/** 自己紹介（profile.md）を置き換える。一時ファイルに書いてから rename し、壊れたファイルを残さない。 */
export async function saveProfile(contentRoot: string, markdown: string): Promise<void> {
  validateFrontmatter(markdown, profileSchema);
  const dir = join(contentRoot, PROFILE_PATH[0]);
  await mkdir(dir, { recursive: true });
  const tmp = join(dir, `.profile.${randomUUID()}.tmp`);
  try {
    await writeFile(tmp, markdown, "utf8");
    await rename(tmp, join(dir, PROFILE_PATH[1]));
  } catch (e) {
    await rm(tmp, { force: true });
    throw e;
  }
}

/** 記事 `articles/<slug>.md` を新規作成し、作成したパスを返す。 */
export async function createArticle(contentRoot: string, slug: string, markdown: string): Promise<string> {
  assertValidSlug(slug);
  validateFrontmatter(markdown, articleSchema);
  const dir = join(contentRoot, "articles");
  await mkdir(dir, { recursive: true });
  const path = join(dir, `${slug}.md`);
  await writeNew(path, markdown);
  return path;
}

export type NewPortfolio = { slug: string; title: string; tags: string[]; url?: string; date?: string };

const PORTFOLIO_BODY = "\n## 概要\n\n（ここにポートフォリオの内容を書く）\n";

/** ポートフォリオ `portfolios/<slug>.md` を雛形の本文付きで新規作成し、作成したパスを返す。 */
export async function createPortfolio(contentRoot: string, input: NewPortfolio): Promise<string> {
  assertValidSlug(input.slug);
  const data: Record<string, unknown> = { title: input.title, tags: input.tags };
  if (input.url !== undefined) data.url = input.url;
  if (input.date !== undefined) data.date = input.date;
  const markdown = stringifyMarkdown(data, PORTFOLIO_BODY);
  validateFrontmatter(markdown, portfolioSchema);
  const dir = join(contentRoot, "portfolios");
  await mkdir(dir, { recursive: true });
  const path = join(dir, `${input.slug}.md`);
  await writeNew(path, markdown);
  return path;
}
