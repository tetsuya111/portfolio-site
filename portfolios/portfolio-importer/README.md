# portfolio-importer

指定したプロジェクトをポートフォリオとして取り込むコマンド。Claude Code のスキル [/add-portfolio](../../.claude/skills/add-portfolio/SKILL.md) から呼び出す。Python 3.12 の標準ライブラリだけで動く（追加のインストール不要）。

## 使い方

リポジトリのルートで実行する。

```bash
python portfolios/portfolio-importer/add_portfolio.py <プロジェクトのパス> [--slug <スラッグ>] [--site-url <URL>]
```

| 引数 | 内容 |
|---|---|
| `<プロジェクトのパス>` | 取り込むディレクトリ。`portfolios/` 配下ならコピーせずそのまま使う |
| `--slug` | スラッグ（省略時はディレクトリ名から作る）。英小文字・数字・ハイフン。`docs`・`docker-images`・`portfolio-importer` は使えない |
| `--site-url` | 任意。フロントエンドを配信登録したとき、掲載 md の `url` を絶対 URL `<URL>/apps/<スラッグ>/` にする。省略時はサイト内のパス `/apps/<スラッグ>/` にする（本番・dev のどちらのサイトでも、表示中のドメインのアプリが開く）。配信登録しなかったときは、`portfolios/docs/<スラッグ>.md` の http(s) の `url` を使う |

結果は JSON で標準出力に出る。エラー時は理由を標準エラーに出し、終了コード 1 で終わる。

## 行うこと

| 順 | 内容 | 作成・変更するもの |
|---|---|---|
| 1 | プロジェクトのコピー。各階層の `.gitignore` に一致するもの、`.git/`・`node_modules/`・`.venv/`・`venv/`・`__pycache__/`、DB（`*.sqlite`・`*.sqlite3`・`*.db` など）、`*.pyc`、`.env`・`.env.*`（`.env.example` を除く）、鍵・証明書（`*.pem`・`*.key`・`*.p12`・`*.pfx`）、`*.jks`・`*.keystore`・`*.secret`・`id_rsa*`・`id_ed25519*`・`secrets.*`、`.npmrc`、`credentials*.json`・`service-account*.json`、シンボリックリンクはコピーしない。フロントエンドを `apps/` にコピーするときも、プロジェクトのルートの `.gitignore` を適用する | `portfolios/<スラッグ>/` |
| 2 | node 製フロントエンド（`frontend/`・`web/`・`client/`・ルート）の検出。Vite（SvelteKit・Nuxt などのメタフレームワークを除く）・静的出力の Astro・`output: "export"`・`basePath: "/apps/<スラッグ>"`・`trailingSlash: true` を設定した Next.js だけを、`package-lock.json` があるときに配信登録する。ルートにあるフロントエンドをコピーするときは、バックエンドのディレクトリを除く | `portfolio-site/apps/<スラッグ>/`、`portfolio-site/apps/apps.json`（[配信の仕組み](../../portfolio-site/docs/apps.md)） |
| 3 | バックエンド（`backend/`・`server/`・`api/`・ルート。Python / node）があり、フロントエンドを配信登録した場合に、モックの雛形を作る。バックエンドのソース（テストを除く）から FastAPI・Flask のルートデコレーター（`@app.get("/x")`・`@app.route("/x", methods=[...])`）と node の `app.get("/x", ...)` 形式のルートを探し、ルートごとに、404 を返す `portfolioMock.handle(..., () => portfolioMock.notFound())` を書く（パスの `{id}`・`<int:id>` は `:id` にする。router の prefix は解決しない。`axios.get` などの HTTP クライアントの呼び出しと、バックエンド配下のフロントエンドは除く。`/`・`/:slug` のように固定の区間がないルートは、静的ファイルの取得まで横取りするため書かずに警告する）。`apps.json` の項目には `"mock": true` を入れる | `portfolio-site/apps/<スラッグ>/mock/handlers.js`（[モックの仕組み](../../portfolio-site/docs/apps.md#バックエンドのモック)） |
| 4 | 掲載 md の作成。`portfolios/docs/<スラッグ>.md` → README → スラッグの順で情報を使う | `portfolio-site/src/content/portfolios/<スラッグ>.md` |

- 既にあるファイル（コピー先以外）は上書きせず、`warnings` に出す。コピー先 `portfolios/<スラッグ>/` が既にあるとエラー。
- リポジトリ外には書き込まない。
- バックエンドは配信しない（S3 で完結させるため、Dockerfile の生成やイメージの作成は行わない）。フロントエンドはモックの応答で動く。

## 出力（JSON）

| 項目 | 内容 |
|---|---|
| `slug`・`projectDir`・`copied` | スラッグ、取り込み先、コピーしたか |
| `frontend` | `{dir, kind, registered, mock}`。`mock` は作成した（または既にある）`handlers.js` のパス。作らなかった場合は null |
| `backend` | `{dir, kind, routes}`。`routes` は検出したルートの数 |
| `content` | 作成した掲載 md のパス（既にあれば null） |
| `warnings` | 警告の一覧 |

## 開発

```bash
cd portfolios/portfolio-importer
npm test      # python -m unittest
npm run lint  # 構文チェック（python -m compileall）
```

設計: [docs/specs/add-portfolio/](../../docs/specs/add-portfolio/design.md)・[docs/specs/add-portfolio-mock-backend/](../../docs/specs/add-portfolio-mock-backend/design.md)
