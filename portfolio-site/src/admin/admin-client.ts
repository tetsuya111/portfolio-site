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

// 保存で md が変わると、開発サーバーが管理画面を再読み込みすることがある。
// 結果のメッセージが消えないよう sessionStorage にも残し、読み込み直後に表示し直す。
const STATUS_KEY = "admin-status";
const STATUS_TTL_MS = 10_000;

function renderStatus(ok: boolean, message: string): void {
  const status = document.getElementById("status");
  if (!status) return;
  status.className = `mt-4 whitespace-pre-wrap text-sm ${ok ? "text-green-700" : "text-red-700"}`;
  status.textContent = message;
}

function showStatus(ok: boolean, message: string): void {
  renderStatus(ok, message);
  try {
    sessionStorage.setItem(STATUS_KEY, JSON.stringify({ ok, message, at: Date.now(), path: location.pathname }));
  } catch {
    // 保存できなくても表示はできているので続ける
  }
}

/** 直前（10秒以内）に同じ画面で表示した結果のメッセージがあれば表示し直す。各管理画面の読み込み時に呼ぶ。 */
export function restoreStatus(): void {
  try {
    const raw = sessionStorage.getItem(STATUS_KEY);
    sessionStorage.removeItem(STATUS_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw) as { ok: boolean; message: string; at: number; path: string };
    if (saved.path === location.pathname && Date.now() - saved.at < STATUS_TTL_MS) {
      renderStatus(saved.ok, saved.message);
    }
  } catch {
    // 読み出せない場合は表示しないだけ
  }
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
