// apps/apps.json に登録したポートフォリオのフロントエンドをビルドし、dist/apps/<スラッグ>/ に置くコマンド
// （npm run build:apps から tsx で実行する。astro build の後に実行すること）
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { buildApps, validateManifest } from "../src/lib/apps-manifest.ts";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const appsDir = join(root, "apps");

// Windows の npm は npm.cmd のためシェル経由で起動する（引数は validateManifest で安全な文字に限定済み）
const run = (cmd, args, cwd) => {
  const r = spawnSync(cmd, args, { cwd, stdio: "inherit", shell: process.platform === "win32" });
  if (r.error) console.error(r.error.message);
  return r.status ?? 1;
};

try {
  const apps = validateManifest(JSON.parse(readFileSync(join(appsDir, "apps.json"), "utf8")));
  buildApps(apps, { appsDir, distDir: join(root, "dist"), run });
  console.log(`${apps.length} 件のアプリをビルドしました`);
} catch (e) {
  console.error(`apps のビルドに失敗しました: ${e instanceof Error ? e.message : e}`);
  process.exitCode = 1;
}
