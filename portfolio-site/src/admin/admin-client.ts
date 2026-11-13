// 管理画面のブラウザ側で使う共通処理

/** 保存 API に JSON を送り、結果を #status に表示する。通信自体の失敗も表示する。 */
export async function sendJson(method: "PUT" | "POST", path: string, body: unknown, successMessage: string): Promise<boolean> {
  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    showStatus(false, `送信できませんでした（開発サーバーが起動しているか確認してください）: ${e instanceof Error ? e.message : String(e)}`);
    return false;
  }
  return showResult(res, successMessage);
}

function showStatus(ok: boolean, message: string): void {
  const status = document.getElementById("status");
  if (!status) return;
  status.className = `mt-4 whitespace-pre-wrap text-sm ${ok ? "text-green-700" : "text-red-700"}`;
  status.textContent = message;
}

/** API の応答を #status に表示する。 */
async function showResult(res: Response, successMessage: string): Promise<boolean> {
  let json: { error?: string; issues?: string[] } = {};
  try {
    json = await res.json();
  } catch {
    // JSON でない応答は下のメッセージで扱う
  }
  showStatus(
    res.ok,
    res.ok
      ? successMessage
      : [`保存できませんでした（${res.status}）: ${json.error ?? "不明なエラー"}`, ...(json.issues ?? [])].join("\n- "),
  );
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
