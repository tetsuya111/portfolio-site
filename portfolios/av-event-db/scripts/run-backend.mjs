// backend/.venv の Python でコマンドを実行する（Windows・macOS・Linux 共通）。
// 例: node scripts/run-backend.mjs -m pytest
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const backendDir = join(dirname(fileURLToPath(import.meta.url)), "..", "backend");
const candidates =
  process.platform === "win32"
    ? [join(backendDir, ".venv", "Scripts", "python.exe")]
    : [join(backendDir, ".venv", "bin", "python")];
const python = candidates.find((p) => existsSync(p));

if (!python) {
  console.error(
    "backend/.venv が見つかりません。README の「セットアップ」に従って venv を作成してください。",
  );
  process.exit(1);
}

// npm スクリプトはローカル開発用のため、APP_ENV が未設定なら development にする
// （Django 側の既定は本番扱い。本番では APP_ENV と DJANGO_SECRET_KEY を明示する）
const env = { ...process.env, APP_ENV: process.env.APP_ENV || "development" };
const result = spawnSync(python, process.argv.slice(2), { cwd: backendDir, stdio: "inherit", env });
process.exit(result.status ?? 1);
