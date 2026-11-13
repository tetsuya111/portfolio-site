// 管理画面のブラウザ側で使う共通処理

/** API の応答を #status に表示する。 */
export async function showResult(res: Response, successMessage: string): Promise<boolean> {
  const status = document.getElementById("status");
  let json: { error?: string; issues?: string[] } = {};
  try {
    json = await res.json();
  } catch {
    // JSON でない応答は下のメッセージで扱う
  }
  if (status) {
    status.className = `mt-4 whitespace-pre-wrap text-sm ${res.ok ? "text-green-700" : "text-red-700"}`;
    status.textContent = res.ok
      ? successMessage
      : [`保存できませんでした（${res.status}）: ${json.error ?? "不明なエラー"}`, ...(json.issues ?? [])].join("\n- ");
  }
  return res.ok;
}

/** フォームの入力値から記事の md 全文を組み立てる。値は JSON 文字列として書き出す（YAML として有効）。 */
export function buildArticleMarkdown(input: {
  title: string;
  date: string;
  tags: string[];
  description: string;
  draft: boolean;
  body: string;
}): string {
  const lines = [
    "---",
    `title: ${JSON.stringify(input.title)}`,
    `date: ${JSON.stringify(input.date)}`,
    `tags: ${JSON.stringify(input.tags)}`,
  ];
  if (input.description) lines.push(`description: ${JSON.stringify(input.description)}`);
  if (input.draft) lines.push("draft: true");
  lines.push("---", "", input.body.endsWith("\n") ? input.body : `${input.body}\n`);
  return lines.join("\n");
}
