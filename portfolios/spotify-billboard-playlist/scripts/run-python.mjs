// backend/.venv の Python を OS に依存せず cwd=backend で起動する。
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const backend = join(dirname(fileURLToPath(import.meta.url)), "..", "backend");
const python =
  process.platform === "win32"
    ? join(backend, ".venv", "Scripts", "python.exe")
    : join(backend, ".venv", "bin", "python");

if (!existsSync(python)) {
  console.error("backend/.venv がありません。先に `npm run setup` を実行してください。");
  process.exit(1);
}

const result = spawnSync(python, process.argv.slice(2), { cwd: backend, stdio: "inherit" });
if (result.error) {
  console.error(`起動に失敗しました: ${result.error.message}`);
}
process.exit(result.status ?? 1);
