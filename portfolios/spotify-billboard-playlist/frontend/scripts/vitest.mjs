// Windows でカレントディレクトリのドライブ文字が小文字（c:\…）だと vitest が
// 自身を二重に読み込み「failed to find the current suite」等で失敗するため、
// ドライブ文字を大文字に正規化してから vitest を起動する。
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const upperDrive = (p) => p.replace(/^([a-z]):/, (_, d) => `${d.toUpperCase()}:`);
const cwd = upperDrive(process.cwd());
const bin = upperDrive(
  join(dirname(fileURLToPath(import.meta.url)), "..", "node_modules", "vitest", "vitest.mjs"),
);
const result = spawnSync(process.execPath, [bin, ...process.argv.slice(2)], { cwd, stdio: "inherit" });
process.exit(result.status ?? 1);
