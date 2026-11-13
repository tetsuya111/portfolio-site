// 開発サーバー（astro dev）でだけ管理画面と保存 API を有効にする Astro インテグレーション。
// 本番ビルド（astro build）では何も登録しないため、成果物に管理画面・API は含まれない（R19・R20）。
import type { IncomingMessage } from "node:http";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { AstroIntegration } from "astro";
import { ADMIN_API_PREFIX, MAX_BODY_BYTES, handleAdminRequest } from "../src/lib/admin-api";

export const ADMIN_ROUTES = [
  { pattern: "/admin", entrypoint: "../src/admin/index.astro" },
  { pattern: "/admin/profile", entrypoint: "../src/admin/profile.astro" },
  { pattern: "/admin/articles/new", entrypoint: "../src/admin/article-new.astro" },
] as const;

/** 管理画面のページ（src/admin/*.astro）から保存先ディレクトリを参照するための定数名 */
export const CONTENT_ROOT_DEFINE = "__ADMIN_CONTENT_ROOT__";

export class BodyTooLargeError extends Error {
  constructor(limit: number) {
    super(`リクエスト本文が上限（${limit} バイト）を超えています`);
    this.name = "BodyTooLargeError";
  }
}

/** リクエスト本文を上限付きで読み、UTF-8 文字列として返す。上限を超えたら BodyTooLargeError。 */
export async function readBodyWithLimit(req: IncomingMessage, limit: number): Promise<string> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    const buf = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk as string);
    size += buf.length;
    if (size > limit) throw new BodyTooLargeError(limit);
    chunks.push(buf);
  }
  return Buffer.concat(chunks).toString("utf8");
}

function normalizeHeaders(req: IncomingMessage): Record<string, string | undefined> {
  const out: Record<string, string | undefined> = {};
  for (const [k, v] of Object.entries(req.headers)) out[k] = Array.isArray(v) ? v[0] : v;
  return out;
}

export function localAdmin(options: { contentRoot: string }): AstroIntegration {
  let contentRoot = options.contentRoot;

  return {
    name: "local-admin",
    hooks: {
      "astro:config:setup": ({ command, injectRoute, config, updateConfig }) => {
        if (command !== "dev") return;
        if (config?.root) contentRoot = resolve(fileURLToPath(config.root), options.contentRoot);
        // 管理画面が表示に使う保存先を、保存 API と同じ値にそろえる
        updateConfig({ vite: { define: { [CONTENT_ROOT_DEFINE]: JSON.stringify(contentRoot) } } });
        for (const route of ADMIN_ROUTES) {
          injectRoute({ pattern: route.pattern, entrypoint: new URL(route.entrypoint, import.meta.url) });
        }
      },
      "astro:server:setup": ({ server, logger }) => {
        logger.info(`管理画面: /admin（保存先: ${contentRoot}）`);
        server.middlewares.use(async (req, res, next) => {
          const path = (req.url ?? "").split("?")[0] ?? "";
          if (!path.startsWith(ADMIN_API_PREFIX)) return next();
          const send = (status: number, json: unknown) => {
            res.statusCode = status;
            res.setHeader("Content-Type", "application/json; charset=utf-8");
            res.end(JSON.stringify(json));
          };
          try {
            const body = await readBodyWithLimit(req, MAX_BODY_BYTES);
            const result = await handleAdminRequest(
              { method: req.method ?? "", path, headers: normalizeHeaders(req), body },
              { contentRoot },
            );
            send(result.status, result.json);
          } catch (e) {
            if (e instanceof BodyTooLargeError) return send(413, { error: e.message });
            logger.error(`保存 API でエラー: ${e instanceof Error ? e.message : String(e)}`);
            send(500, { error: "保存中にエラーが発生しました" });
          }
        });
      },
    },
  };
}
