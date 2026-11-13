// `npm run portfolio:new` の引数解析と実行。サイト上からはポートフォリオを追加できない（R11）ため、
// 追加はこのコマンドだけで行う。
import { parseArgs } from "node:util";
import { createPortfolio, type NewPortfolio } from "./content-store";
import { ContentConflictError, ContentValidationError } from "./errors";
import { formatIssues, portfolioSchema } from "./schemas";
import { assertValidSlug } from "./slug";

export const USAGE =
  '使い方: npm run portfolio:new -- --slug <スラッグ> --title "<タイトル>" [--tags "タグ1,タグ2"] [--url <URL>]';

export type PortfolioArgs = Omit<NewPortfolio, "date">;

export function parsePortfolioArgs(argv: string[]): PortfolioArgs {
  let values: Record<string, string | undefined>;
  try {
    ({ values } = parseArgs({
      args: argv,
      strict: true,
      allowPositionals: false,
      options: {
        slug: { type: "string" },
        title: { type: "string" },
        tags: { type: "string" },
        url: { type: "string" },
      },
    }));
  } catch (e) {
    throw new ContentValidationError([(e as Error).message]);
  }

  const issues: string[] = [];
  const title = values.title?.trim() ?? "";
  if (!values.slug) issues.push("--slug が必要です（英小文字・数字・ハイフン。日本語タイトルからは自動生成しません）");
  if (!title) issues.push("--title が必要です");
  if (issues.length > 0) throw new ContentValidationError(issues);

  const slug = values.slug as string;
  assertValidSlug(slug);
  const tags = (values.tags ?? "")
    .split(",")
    .map((t) => t.trim())
    .filter((t) => t.length > 0);
  const result: PortfolioArgs = { slug, title, tags };
  if (values.url !== undefined) result.url = values.url;

  const check = portfolioSchema.safeParse(result);
  if (!check.success) throw new ContentValidationError(formatIssues(check.error));
  return result;
}

function formatDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** コマンド本体。終了コードと表示メッセージを返す（標準出力・終了処理は呼び出し側）。 */
export async function runNewPortfolio(
  argv: string[],
  contentRoot: string,
  today: Date = new Date(),
): Promise<{ exitCode: 0 | 1; message: string }> {
  try {
    const args = parsePortfolioArgs(argv);
    const path = await createPortfolio(contentRoot, { ...args, date: formatDate(today) });
    return { exitCode: 0, message: `作成しました: ${path}\n本文（## 概要 以下）を編集してください。` };
  } catch (e) {
    if (e instanceof ContentValidationError) {
      return { exitCode: 1, message: `エラー:\n- ${e.issues.join("\n- ")}\n${USAGE}` };
    }
    if (e instanceof ContentConflictError) return { exitCode: 1, message: `エラー: ${e.message}` };
    throw e;
  }
}
