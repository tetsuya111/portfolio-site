// ポートフォリオのフロントエンド（apps/<スラッグ>/）を S3 で配信するための管理ファイル apps/apps.json の
// 検証とビルド。デプロイ時に scripts/build-apps.mjs から呼び、成果物を dist/apps/<スラッグ>/ に置く
// （dist は buildspec の s3 sync でそのまま配信される）。apps.json は portfolio-importer が追記する。
import { cpSync, existsSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { isAbsolute, join, normalize, sep } from "node:path";
import { isValidSlug } from "./slug";

export interface AppEntry {
  slug: string;
  /** ビルド成果物のディレクトリ（アプリのディレクトリからの相対パス） */
  outputDir: string;
  /** `npm run build -- <buildArgs>` に渡す引数 */
  buildArgs: string[];
  /** true なら mock/handlers.js のモックを出力の HTML に差し込み、バックエンドなしで動かす */
  mock: boolean;
  /** ビルド時の環境変数（バックエンドの URL など。backend-compose が書く）。npm ci・npm run build に渡す */
  env: Record<string, string>;
}

/** シェルを経由しても安全な文字だけの引数（Windows では npm をシェル経由で起動するため） */
const SAFE_ARG = /^[\w@./:=-]+$/;
/**
 * env の名前は公開用の接頭辞を持つものだけ（NODE_OPTIONS・PATH などビルドの挙動を変える変数を入れさせない）。
 * 値は https の URL で、シェルを経由しても安全な文字だけ（サイトは HTTPS のため http の API は呼べない）
 */
const ENV_NAME = /^(?:VITE_|PUBLIC_|NEXT_PUBLIC_)[A-Z0-9_]+$/;
const ENV_VALUE = /^https:\/\/[A-Za-z0-9.\-_~/:%]+$/;

function validateEnv(env: unknown, where: string): Record<string, string> {
  if (env === undefined) return {};
  if (typeof env !== "object" || env === null || Array.isArray(env)) {
    throw new Error(`${where}.env は {"環境変数名": "値"} の形にしてください`);
  }
  const out: Record<string, string> = {};
  for (const [name, value] of Object.entries(env)) {
    if (!ENV_NAME.test(name)) throw new Error(`${where}.env の名前「${name}」は VITE_・PUBLIC_・NEXT_PUBLIC_ で始まる英大文字・数字・_ にしてください`);
    if (typeof value !== "string" || !ENV_VALUE.test(value)) {
      throw new Error(`${where}.env.${name} は https:// で始まる URL（英数字と . - _ ~ / : % だけ）にしてください`);
    }
    out[name] = value;
  }
  return out;
}

function isSafeRelativeDir(dir: string): boolean {
  if (dir === "" || isAbsolute(dir) || /^[A-Za-z]:/.test(dir) || dir.includes("\\")) return false;
  // アプリのディレクトリ自体（"./" など）を指すとソースや node_modules まで配信されるため拒否する
  const n = normalize(dir).replace(/\\/g, "/").replace(/\/+$/, "");
  return n !== "" && n !== "." && n !== ".." && !n.startsWith("../") && !dir.split("/").includes("..");
}

/** apps.json の内容を検証してアプリの一覧を返す。不正なら理由を含む Error を投げる。 */
export function validateManifest(data: unknown): AppEntry[] {
  const apps = (data as { apps?: unknown } | null)?.apps;
  if (!Array.isArray(apps)) throw new Error('apps.json は {"apps": [...]} の形にしてください');
  const seen = new Set<string>();
  return apps.map((raw, i) => {
    const a = raw as Partial<AppEntry> | null;
    const where = `apps[${i}]`;
    if (typeof a?.slug !== "string" || !isValidSlug(a.slug)) throw new Error(`${where}.slug が不正です`);
    if (seen.has(a.slug)) throw new Error(`${where}.slug「${a.slug}」が重複しています`);
    seen.add(a.slug);
    if (typeof a.outputDir !== "string" || !isSafeRelativeDir(a.outputDir)) {
      throw new Error(`${where}.outputDir はアプリ内の相対パスにしてください`);
    }
    if (!Array.isArray(a.buildArgs) || !a.buildArgs.every((x) => typeof x === "string" && SAFE_ARG.test(x))) {
      throw new Error(`${where}.buildArgs は英数字と @ . / : = - _ だけの文字列の配列にしてください`);
    }
    if (a.mock !== undefined && typeof a.mock !== "boolean") throw new Error(`${where}.mock は true か false にしてください`);
    const env = validateEnv((raw as { env?: unknown }).env, where);
    return { slug: a.slug, outputDir: a.outputDir, buildArgs: [...a.buildArgs], mock: a.mock ?? false, env };
  });
}

export interface BuildOptions {
  appsDir: string;
  distDir: string;
  /** コマンドを実行して終了コードを返す。env は実行環境の環境変数に追加して渡す */
  run: (cmd: string, args: string[], cwd: string, env: Record<string, string>) => number;
  /** モックのランタイム（src/lib/mock-runtime.js）のパス。mock: true のアプリがあるときに必要 */
  mockRuntime?: string;
}

/** アプリ内のモックのハンドラー（importer が雛形を作る） */
const MOCK_HANDLERS = join("mock", "handlers.js");

function htmlFiles(dir: string): string[] {
  return readdirSync(dir, { recursive: true, withFileTypes: true })
    .filter((e) => e.isFile() && e.name.toLowerCase().endsWith(".html"))
    .map((e) => join(e.parentPath, e.name));
}

/** HTML 文書か（部分 HTML（fetch して差し込む断片など）にはスクリプトを入れない） */
const HTML_DOCUMENT = /<!doctype\s|<html[\s>]|<head[\s>]/i;

/** <head> の直後（なければ doctype の後、それもなければ先頭）にタグを差し込む */
export function injectIntoHead(html: string, tags: string): string {
  for (const re of [/<head(?:\s[^>]*)?>/i, /^\s*<!doctype[^>]*>/i]) {
    const m = re.exec(html);
    if (m) return html.slice(0, m.index + m[0].length) + tags + html.slice(m.index + m[0].length);
  }
  return tags + html;
}

/** ランタイムとハンドラーを <out>/__mock__/ に置き、各 HTML から読み込ませる */
function installMock(slug: string, cwd: string, out: string, runtime: string): void {
  const dir = join(out, "__mock__");
  cpSync(runtime, join(dir, "runtime.js"));
  cpSync(join(cwd, MOCK_HANDLERS), join(dir, "handlers.js"));
  // slug は isValidSlug で英小文字・数字・ハイフンに限定済みのため、そのまま HTML に埋めてよい
  const base = `/apps/${slug}`;
  const tags =
    `<script src="${base}/__mock__/runtime.js" data-base="${base}"></script>` +
    `<script src="${base}/__mock__/handlers.js"></script>`;
  for (const file of htmlFiles(out)) {
    if (file.startsWith(dir + sep)) continue;
    const html = readFileSync(file, "utf8");
    if (HTML_DOCUMENT.test(html)) writeFileSync(file, injectIntoHead(html, tags));
  }
}

/** 各アプリを npm でビルドし、成果物を <distDir>/apps/<スラッグ>/ にコピーする。失敗したら Error を投げる。 */
export function buildApps(apps: AppEntry[], { appsDir, distDir, run, mockRuntime }: BuildOptions): void {
  for (const app of apps) {
    const cwd = join(appsDir, app.slug);
    if (!existsSync(join(cwd, "package.json"))) {
      throw new Error(`${app.slug}: apps/${app.slug}/package.json がありません`);
    }
    // デプロイ用の権限があるビルド環境で動くため、依存は lockfile で固定したものだけを入れる
    if (!existsSync(join(cwd, "package-lock.json"))) {
      throw new Error(`${app.slug}: apps/${app.slug}/package-lock.json がありません（依存のバージョンを固定してください）`);
    }
    if (app.mock && !existsSync(join(cwd, MOCK_HANDLERS))) {
      throw new Error(`${app.slug}: apps/${app.slug}/mock/handlers.js がありません（mock: true のため必要です）`);
    }
    const runtime = app.mock ? mockRuntime : undefined;
    if (app.mock && (runtime === undefined || !existsSync(runtime))) {
      throw new Error(`${app.slug}: モックのランタイムが見つかりません`);
    }
    const build = ["run", "build", ...(app.buildArgs.length ? ["--", ...app.buildArgs] : [])];
    // インストールスクリプトは実行しない（乗っ取られた依存のスクリプトにデプロイ用の権限を使わせない）
    for (const args of [["ci", "--ignore-scripts"], build]) {
      const code = run("npm", args, cwd, app.env);
      if (code !== 0) throw new Error(`${app.slug}: npm ${args.join(" ")} が失敗しました（終了コード ${code}）`);
    }
    const out = join(cwd, app.outputDir);
    if (!existsSync(out) || !statSync(out).isDirectory()) {
      throw new Error(`${app.slug}: ビルド成果物 ${app.outputDir} がありません`);
    }
    const dest = join(distDir, "apps", app.slug);
    // 前回のビルドの残り（消えたページなど）に、モックを二重に差し込まないよう空にしてからコピーする
    rmSync(dest, { recursive: true, force: true });
    cpSync(out, dest, { recursive: true });
    if (runtime !== undefined) installMock(app.slug, cwd, dest, runtime);
  }
}

/** ポートフォリオのフロントエンドが、モックの応答で動くか（mock）、実際のバックエンドを呼ぶか（api） */
export type AppBackendMode = "mock" | "api";

/** apps.json の内容から、スラッグごとの動作（モック／実 API）を返す。不正なら空（ボタンを今の表示にする） */
export function appBackendModes(data: unknown): Map<string, AppBackendMode> {
  try {
    return new Map(validateManifest(data).map((a) => [a.slug, a.mock ? "mock" : "api"] as const));
  } catch {
    return new Map();
  }
}

/** apps/apps.json（既定は portfolio-site で実行したときの場所）を読んで appBackendModes を返す。読めなければ空 */
export function readAppBackendModes(path = join(process.cwd(), "apps", "apps.json")): Map<string, AppBackendMode> {
  try {
    return appBackendModes(JSON.parse(readFileSync(path, "utf8")));
  } catch {
    return new Map();
  }
}
