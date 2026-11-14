# 設計: 取り込んだフロントエンドをバックエンドのモックと接続する

要件: [requirements.md](requirements.md)

## TL;DR

- importer は、バックエンドのルート定義から `portfolio-site/apps/<スラッグ>/mock/handlers.js` の雛形を作り、`apps.json` の項目に `"mock": true` を入れる。Dockerfile の生成とイメージ作成はなくす。
- portfolio-site の `npm run build:apps` は、`mock: true` のアプリの出力 HTML の `<head>` 直後に `__mock__/runtime.js`・`__mock__/handlers.js` の `<script>` を差し込む。
- `runtime.js`（依存なし）が `window.fetch` を差し替え、登録したメソッド・パスに一致するリクエストにハンドラーの戻り値で応答する。通信しないため S3 だけで動く。
- スキル `/add-portfolio` は、雛形のハンドラーにバックエンドのコードとフロントエンドの型から応答データを書く。

## Non-Goals

requirements.md のとおり。XHR・ページ遷移の横取り、応答データの自動生成、`npm run dev` でのモックは扱わない。

## 全体構成

```
/add-portfolio <パス>（スキル）
  ├ python portfolios/portfolio-importer/add_portfolio.py <パス> [--slug] [--site-url]
  │    importer/cli.py       全体の順序・JSON 出力（R1-9, R4-1, R4-3）
  │    importer/frontend.py  apps/ へのコピーと apps.json 登録。mock: true を入れる（R1-7, R1-8）
  │    importer/mock.py      【新規】ルートの検出と handlers.js の雛形の生成（R1-1〜R1-6）
  │    importer/backend.py   【削除】Dockerfile 生成・docker build/save（R4-1, R4-2）
  └ 雛形のハンドラーに応答データを書く（Claude, R5-1）
portfolio-site/
  apps/apps.json                    "mock": true（R2-1）
  apps/<スラッグ>/mock/handlers.js  ハンドラー（importer が雛形を作り、スキルが中身を書く）
  src/lib/mock-runtime.js           【新規】ブラウザで動くモックのランタイム（R3-*）
  src/lib/apps-manifest.ts          mock の検証、__mock__ への配置と HTML への差し込み（R2-*）
  scripts/build-apps.mjs            ランタイムのパスを buildApps に渡す
```

## 詳細設計

### handlers.js の書式（R3-1, R3-3〜R3-5）

```js
// portfolio-importer が生成したモック。...
portfolioMock.handle("GET", "/api/me", (req) => {
  return { logged_in: true, display_name: "Demo User" };
});
portfolioMock.handle("POST", "/api/items/:id", (req) => {
  // req = { method, path, params: { id }, query: URLSearchParams, body }
  return { id: req.params.id };
});
```

- 戻り値: `Response` → そのまま／`undefined`・`null` → 204／それ以外 → `JSON.stringify` して 200・`Content-Type: application/json`。`async` 関数（Promise）も可。
- 状態コードを変えたいときは `new Response(...)` を返す。

### ランタイム（`src/lib/mock-runtime.js`, R3-*）

即時関数1つ。`<script src=".../runtime.js" data-base="/apps/<スラッグ>">` として読み込まれる。

1. `document.currentScript.dataset.base` から配信パスを得る。
2. `window.portfolioMock = { handle(method, path, fn) }` を定義する。パスは末尾の `/` を除き、`/` で区切った区間の配列として保持する。
3. `window.fetch` を差し替える。`new Request(input, init)` でメソッドと URL を得て、`URL.pathname` と、配信パスで始まればそれを除いたパスの両方で、登録順に一致を探す（R3-6）。オリジンは、アプリと同じものと `localhost`・`127.0.0.1`・`[::1]` だけを対象にする（開発時のバックエンド URL のまま呼ぶフロントエンドに効かせ、外部 API は横取りしない）。パスの引数は静的ファイルの拡張子（`.txt`・`.json`・`.js`・画像・フォントなど）で終わる区間に一致させない。
4. 一致したら `request.text()` の本文を JSON として読めれば変換し、ハンドラーを呼ぶ。例外は `console.error` して 500（R3-8）。一致しなければ元の `fetch(input, init)`（R3-7）。

`<head>` 直後の同期スクリプトのため、アプリの `type="module"`・`defer`・`async` のスクリプトより先に実行される。

### ビルド（`apps-manifest.ts`, R2-*）

- `validateManifest`: `mock` は省略時 false、真偽値以外はエラー。戻り値の `AppEntry` に `mock: boolean` を持たせる。
- `buildApps` の `BuildOptions` に `mockRuntime`（ランタイムのファイルパス）を追加する。成果物を `dist/apps/<スラッグ>/` にコピーした後、`mock` なら:
  1. `apps/<スラッグ>/mock/handlers.js` がなければエラー（R2-4）。ビルド前に確認し、無駄なビルドをしない。
  2. ランタイムと handlers.js を `dist/apps/<スラッグ>/__mock__/runtime.js`・`handlers.js` にコピーする（R2-2）。
  3. 出力先の `.html` を再帰的に探し、最初の `<head>`（属性付き可、大文字小文字を問わない）の直後に次を差し込む。`<head>` がなければ `<!doctype ...>` の直後、それもなければ先頭（R2-3）。

     ```html
     <script src="/apps/<スラッグ>/__mock__/runtime.js" data-base="/apps/<スラッグ>"></script><script src="/apps/<スラッグ>/__mock__/handlers.js"></script>
     ```

     スラッグは `isValidSlug` で検証済みのため、HTML にそのまま埋めてよい。

### ルートの検出（`importer/mock.py`, R1-2〜R1-4）

バックエンドのディレクトリで `iter_files`（.gitignore 適用済み）を回し、`tests/`・`test/` 配下と `test_*`・`*.test.*`・`*.spec.*` を除く。

| 種類 | 対象ファイル | 正規表現（概要） |
|---|---|---|
| python | `*.py` | `@\w+(?:\.\w+)*\.(get\|post\|put\|patch\|delete)\(\s*["']([^"']+)["']` |
| python（Flask） | `*.py` | `@\w+(?:\.\w+)*\.route\(\s*["']([^"']+)["']([^)]*)\)` の後半から `methods=[...]` を読む（なければ GET） |
| node | `*.js` `*.mjs` `*.cjs` `*.ts` | `\b\w+\.(get\|post\|put\|patch\|delete)\(\s*(["'\`])(/[^"'\`]*)\2` |

- パスの引数 `{name}`・`{name:path}`・`<name>`・`<int:name>` を `:name` に直す（R1-4）。
- 同じメソッドとパスは1つにまとめ、見つけた順に並べる。`APIRouter(prefix=...)`・`include_router(prefix=...)` の前置きは解決しない（スキルの手順で確認する）。

### 雛形の生成（R1-1, R1-5, R1-6）

- ルートごとに `portfolioMock.handle(<メソッド>, <パス>, (req) => { // TODO ...; return {}; });` を書く。文字列は `json.dumps` で JS の文字列リテラルにする。
- ルートが0件なら、書き方の例をコメントだけで書き、警告を出す。
- 既にあれば書かずに警告。

### CLI（R1-9, R4-1, R4-3）

- `--build-image` を削除。`run`（subprocess）の引数も不要になるため削除する。
- フロントエンドを登録するとき `register_frontend(..., mock=backend is not None)` とし、登録した場合だけ雛形を作る。
- 出力: `frontend = {dir, kind, registered, mock}`、`backend = {dir, kind, routes}`。
- タグから `Docker` を除く。

## 検討した代替案

- MSW: lockfile の更新に `npm install`（外部アクセス）が必要で、importer だけでは完結しない。Service Worker が有効になるまで画面の描画を待たせる組み込み処理もフレームワークごとに要る。
- Service Worker を自作する: XHR も横取りできるが、初回の読み込みで Service Worker が有効になるまで待つ仕組みが要る。HTML へのスクリプト差し込みだけでは、アプリの最初の通信に間に合わない。
- アプリの入口（`main.tsx`・`layout.tsx`）にモックの読み込みを書き足す: フレームワーク・ファイル構成ごとに書き換え方が違い、壊れやすい。
- `apps.json` の `env` でモックのオン・オフを渡す: main には `env` がなく、ビルドの環境変数に頼るとアプリ側の対応が必要になる。
- JSON を静的ファイルで置く: CloudFront が GET・HEAD しか通さず POST が動かない。

## 横断的関心事

- **セキュリティ**: ランタイムは同期スクリプトとして全ページで動く。中身はリポジトリ内のファイルだけで、外部から読み込まない。handlers.js はアプリのファイルと同じく公開されるため、秘密情報は書かない（README・apps.md に明記）。差し込む HTML の値はスラッグだけで、検証済み。
- **互換性**: `mock` は任意項目のため、既存の `apps.json` はそのまま通る。
- **テスト**: ランタイムは Node の `Request`・`Response`・`URL` を使い、`new Function("window", "document", code)` で偽の window・document を渡して vitest で検証する。
- **運用**: `npm run dev` ではモックが入らない（Non-Goals）。動作は `npm run build:apps` の成果物を配信して確認する。

## 要件との対応

| 要件 | 設計要素 |
|---|---|
| R1-1〜R1-6 | `importer/mock.py` |
| R1-7, R1-8 | `importer/frontend.py` の `mock` 引数 |
| R1-9 | `importer/cli.py` の出力 |
| R2-1〜R2-4 | `apps-manifest.ts` |
| R3-1〜R3-8 | `src/lib/mock-runtime.js` |
| R4-1〜R4-3 | `importer/backend.py` の削除、`importer/cli.py` |
| R5-1, R5-2 | スキル、importer の README、`portfolio-site/docs/apps.md` |
