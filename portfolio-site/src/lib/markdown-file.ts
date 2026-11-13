import { parse, stringify } from "yaml";
import { ContentValidationError } from "./errors";

// 先頭の `---` 行から次の `---` 行までを frontmatter とみなす（CRLF も許容）
const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/;

export type MarkdownFile = { data: Record<string, unknown>; body: string };

/** md の全文を frontmatter（オブジェクト）と本文に分ける。frontmatter が無い・壊れていればエラー。 */
export function parseMarkdown(text: string): MarkdownFile {
  const m = FRONTMATTER_RE.exec(text);
  if (!m) {
    throw new ContentValidationError(["先頭に --- で囲んだ frontmatter が必要です"]);
  }
  let data: unknown;
  try {
    data = parse(m[1]);
  } catch (e) {
    throw new ContentValidationError([`frontmatter の YAML を解析できません: ${(e as Error).message}`]);
  }
  if (data === null || typeof data !== "object" || Array.isArray(data)) {
    throw new ContentValidationError(["frontmatter は「項目: 値」の形式で書いてください"]);
  }
  return { data: data as Record<string, unknown>, body: text.slice(m[0].length) };
}

/** frontmatter と本文から md の全文を組み立てる。 */
export function stringifyMarkdown(data: Record<string, unknown>, body: string): string {
  return `---\n${stringify(data).trimEnd()}\n---\n${body}`;
}
