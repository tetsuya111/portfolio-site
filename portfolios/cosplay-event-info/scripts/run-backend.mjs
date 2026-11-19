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

const result = spawnSync(python, process.argv.slice(2), { cwd: backendDir, stdio: "inherit" });
process.exit(result.status ?? 1);
