// ポートフォリオを追加するコマンド（npm run portfolio:new から tsx で実行する）
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { runNewPortfolio } from "../src/lib/portfolio-cli.ts";

const contentRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "src", "content");
const { exitCode, message } = await runNewPortfolio(process.argv.slice(2), contentRoot);
(exitCode === 0 ? console.log : console.error)(message);
process.exitCode = exitCode;
