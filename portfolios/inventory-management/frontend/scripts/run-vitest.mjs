// vitest を起動する。Windows で作業ディレクトリのドライブ文字が小文字（c:\）だと、
// vitest が同じモジュールを二重に読み込み「failed to find the current suite」になるため、
// ドライブ文字を大文字にそろえてから起動する。
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const normalize = (p) => p.replace(/^([a-z]):/, (_, d) => `${d.toUpperCase()}:`);
const root = normalize(join(dirname(fileURLToPath(import.meta.url)), ".."));
const vitest = join(root, "node_modules", "vitest", "vitest.mjs");

const result = spawnSync(process.execPath, [vitest, ...process.argv.slice(2)], {
  cwd: root,
  stdio: "inherit",
});
process.exit(result.status ?? 1);
