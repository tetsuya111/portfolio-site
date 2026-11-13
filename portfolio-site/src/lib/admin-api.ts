// 管理画面の保存 API の処理本体。HTTP サーバーから切り離した純粋な関数にしてテストする。
// 開発サーバー（astro dev）からのみ呼ばれ、本番ビルドには含まれない（integrations/local-admin.ts）。
import { createArticle, saveProfile } from "./content-store";
import { ContentConflictError, ContentValidationError } from "./errors";

export const ADMIN_API_PREFIX = "/__admin/api/";
/** リクエスト本文の上限（1 MB）。 */
export const MAX_BODY_BYTES = 1_048_576;

export type AdminRequest = {
  method: string;
  path: string;
  /** ヘッダー名は小文字 */
  headers: Record<string, string | undefined>;
  body: string;
};
export type AdminResponse = { status: number; json: unknown };

const error = (status: number, message: string, issues?: string[]): AdminResponse => ({
  status,
  json: issues ? { error: message, issues } : { error: message },
});

/**
 * 別サイトのページからの送信を拒否する。Origin のホストが Host ヘッダーと一致する場合だけ通す。
 * JSON 以外も拒否するので、ブラウザのクロスサイト送信は必ずプリフライトが必要になる。
 */
function checkRequestSource(req: AdminRequest): AdminResponse | null {
  const { origin, host } = req.headers;
  let originHost: string | null;
  try {
    originHost = origin ? new URL(origin).host : null;
  } catch {
    originHost = null;
  }
  if (!originHost || !host || originHost !== host) {
    return error(403, "このページ以外からの保存はできません");
  }
  const contentType = req.headers["content-type"]?.split(";")[0]?.trim().toLowerCase();
  if (contentType !== "application/json") {
    return error(415, "Content-Type は application/json にしてください");
  }
  return null;
}

function parseJsonObject(body: string): Record<string, unknown> | null {
  try {
    const v: unknown = JSON.parse(body);
    return v !== null && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

type Route = { method: string; handle: (body: Record<string, unknown>, root: string) => Promise<AdminResponse> };

// ポートフォリオの追加はコマンドのみで行うため、ここには用意しない（R11）
const ROUTES: Record<string, Route> = {
  profile: {
    method: "PUT",
    async handle(body, root) {
      if (typeof body.markdown !== "string") return error(400, "markdown（文字列）が必要です");
      await saveProfile(root, body.markdown);
      return { status: 200, json: { ok: true } };
    },
  },
  articles: {
    method: "POST",
    async handle(body, root) {
      if (typeof body.slug !== "string" || typeof body.markdown !== "string") {
        return error(400, "slug と markdown（文字列）が必要です");
      }
      await createArticle(root, body.slug, body.markdown);
      return { status: 201, json: { ok: true, slug: body.slug } };
    },
  },
};

export async function handleAdminRequest(
  req: AdminRequest,
  ctx: { contentRoot: string },
): Promise<AdminResponse> {
  const name = req.path.startsWith(ADMIN_API_PREFIX) ? req.path.slice(ADMIN_API_PREFIX.length) : "";
  const route = Object.hasOwn(ROUTES, name) ? ROUTES[name] : undefined;
  if (!route) return error(404, "見つかりません");
  if (req.method !== route.method) return error(405, `${route.method} で送信してください`);

  const rejected = checkRequestSource(req);
  if (rejected) return rejected;

  const body = parseJsonObject(req.body);
  if (!body) return error(400, "本文が JSON オブジェクトではありません");

  try {
    return await route.handle(body, ctx.contentRoot);
  } catch (e) {
    if (e instanceof ContentValidationError) return error(400, "入力内容が不正です", e.issues);
    if (e instanceof ContentConflictError) return error(409, "同じスラッグの記事が既にあります");
    throw e;
  }
}
