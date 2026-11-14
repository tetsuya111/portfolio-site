// ポートフォリオのフロントエンド（apps/<スラッグ>/）を S3 で配信するための管理ファイル apps/apps.json の
// 検証とビルド。デプロイ時に scripts/build-apps.mjs から呼び、成果物を dist/apps/<スラッグ>/ に置く
// （dist は buildspec の s3 sync でそのまま配信される）。apps.json は portfolio-importer が追記する。
import { cpSync, existsSync, statSync } from "node:fs";
import { isAbsolute, join, normalize } from "node:path";
import { isValidSlug } from "./slug";

export interface AppEntry {
  slug: string;
  /** ビルド成果物のディレクトリ（アプリのディレクトリからの相対パス） */
  outputDir: string;
  /** `npm run build -- <buildArgs>` に渡す引数 */
  buildArgs: string[];
  /** ビルド時に渡す環境変数（公開用の名前と https の URL だけ。バックエンドの URL などを渡す） */
  env: Record<string, string>;
}

/** シェルを経由しても安全な文字だけの引数（Windows では npm をシェル経由で起動するため） */
const SAFE_ARG = /^[\w@./:=-]+$/;
/** ビルドに渡せる環境変数名。公開用の接頭辞に限り、PATH・NODE_OPTIONS などビルドの挙動を変える変数を渡させない */
export const PUBLIC_ENV_NAME = /^(VITE_|PUBLIC_|NEXT_PUBLIC_)[A-Z0-9_]+$/;
/** 環境変数の値として渡せる URL（サイトが HTTPS のため https のみ。クエリ・フラグメントは不可） */
export const HTTPS_URL = /^https:\/\/[A-Za-z0-9.-]+(:[0-9]{1,5})?(\/[A-Za-z0-9._~/-]*)?$/;

function validateEnv(env: unknown, where: string): Record<string, string> {
  if (env === undefined) return {};
  if (typeof env !== "object" || env === null || Array.isArray(env)) {
    throw new Error(`${where}.env は {"名前": "値"} のオブジェクトにしてください`);
  }
  const out: Record<string, string> = {};
  for (const [name, value] of Object.entries(env)) {
    if (!PUBLIC_ENV_NAME.test(name)) {
      throw new Error(`${where}.env の名前「${name}」は VITE_・PUBLIC_・NEXT_PUBLIC_ で始まる英大文字・数字・_ にしてください`);
    }
    if (typeof value !== "string" || !HTTPS_URL.test(value)) {
      throw new Error(`${where}.env.${name} は https:// で始まる URL（クエリなし）にしてください`);
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
    return { slug: a.slug, outputDir: a.outputDir, buildArgs: [...a.buildArgs], env: validateEnv(a.env, where) };
  });
}

export interface BuildOptions {
  appsDir: string;
  distDir: string;
  /** コマンドを実行して終了コードを返す（env は実行環境の環境変数に追加して渡す） */
  run: (cmd: string, args: string[], cwd: string, env: Record<string, string>) => number;
}

/** 各アプリを npm でビルドし、成果物を <distDir>/apps/<スラッグ>/ にコピーする。失敗したら Error を投げる。 */
export function buildApps(apps: AppEntry[], { appsDir, distDir, run }: BuildOptions): void {
  for (const app of apps) {
    const cwd = join(appsDir, app.slug);
    if (!existsSync(join(cwd, "package.json"))) {
      throw new Error(`${app.slug}: apps/${app.slug}/package.json がありません`);
    }
    // デプロイ用の権限があるビルド環境で動くため、依存は lockfile で固定したものだけを入れる
    if (!existsSync(join(cwd, "package-lock.json"))) {
      throw new Error(`${app.slug}: apps/${app.slug}/package-lock.json がありません（依存のバージョンを固定してください）`);
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
    cpSync(out, join(distDir, "apps", app.slug), { recursive: true });
  }
}
