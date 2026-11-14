# portfolio-importer

指定したプロジェクトをポートフォリオとして取り込むコマンド。Claude Code のスキル [/add-portfolio](../../.claude/skills/add-portfolio/SKILL.md) から呼び出す。Python 3.12 の標準ライブラリだけで動く（追加のインストール不要）。

## 使い方

リポジトリのルートで実行する。

```bash
python portfolios/portfolio-importer/add_portfolio.py <プロジェクトのパス> [--slug <スラッグ>] [--site-url <URL>] [--backend-url <URL>] [--build-image]
```

| 引数 | 内容 |
|---|---|
| `<プロジェクトのパス>` | 取り込むディレクトリ。`portfolios/` 配下ならコピーせずそのまま使う |
| `--slug` | スラッグ（省略時はディレクトリ名から作る）。英小文字・数字・ハイフン。`docs`・`docker-images`・`portfolio-importer` は使えない |
| `--site-url` | ポートフォリオサイトの URL。省略時は `portfolio-site/infra/parameters.json` の `DomainName` から `https://<ドメイン>` を使う（なければ URL なし）。掲載 md の `url`（配信登録時の `<URL>/apps/<スラッグ>/`）とバックエンドの `ENV` に使う |
| `--backend-url` | フロントエンドから呼ぶバックエンドの URL（`https://` のみ、クエリなし）。フロントエンドの環境変数名に入れて `apps.json` の `env` に書く |
| `--build-image` | `docker build` でバックエンドのイメージを作り `portfolios/docker-images/<スラッグ>-backend.tar` に保存する（ベースイメージを外部から取得する） |

結果は JSON で標準出力に出る。エラー時は理由を標準エラーに出し、終了コード 1 で終わる。

## 行うこと

| 順 | 内容 | 作成・変更するもの |
|---|---|---|
| 1 | プロジェクトのコピー。各階層の `.gitignore` に一致するもの、`.git/`・`node_modules/`・`.venv/`・`venv/`・`__pycache__/`、DB（`*.sqlite`・`*.sqlite3`・`*.db` など）、`*.pyc`、`.env`・`.env.*`（`.env.example` を除く）、鍵・証明書（`*.pem`・`*.key`・`*.p12`・`*.pfx`）、`*.jks`・`*.keystore`・`*.secret`・`id_rsa*`・`id_ed25519*`・`secrets.*`、`.npmrc`、`credentials*.json`・`service-account*.json`、シンボリックリンクはコピーしない。フロントエンドを `apps/` にコピーするときも、プロジェクトのルートの `.gitignore` を適用する | `portfolios/<スラッグ>/` |
| 2 | node 製フロントエンド（`frontend/`・`web/`・`client/`・ルート）の検出。Vite（SvelteKit・Nuxt などのメタフレームワークを除く）・静的出力の Astro・`output: "export"`・`basePath: "/apps/<スラッグ>"`・`trailingSlash: true` を設定した Next.js だけを、`package-lock.json` があるときに配信登録する。ルートにあるフロントエンドをコピーするときは、バックエンドのディレクトリを除く | `portfolio-site/apps/<スラッグ>/`、`portfolio-site/apps/apps.json`（[配信の仕組み](../../portfolio-site/docs/apps.md)） |
| 3 | バックエンド（`backend/`・`server/`・`api/`・ルート。Python / node）の Dockerfile 生成。起動コマンドは uvicorn の記載・`FastAPI(` の代入・`main.py`・`npm start` から判定する（テストのファイルは見ない）。Python の依存は `requirements.txt` と `[project]` のある `pyproject.toml` から入れ、node は `build` スクリプトがあればビルドしてから開発用の依存を除く | `<バックエンド>/Dockerfile`、`<バックエンド>/.dockerignore` |
| 4 | 環境変数の設定。フロントエンドのソース・`.env.example` から `VITE_`・`PUBLIC_`・`NEXT_PUBLIC_` で始まり `API`・`BACKEND`・`SERVER` と `URL`・`ORIGIN`・`BASE`・`ENDPOINT`・`HOST` を含む名前を探し、名前順の先頭に `--backend-url` を入れる（登録済みなら未設定の名前だけ追加）。バックエンドのソース（テストを除く）・`.env.example` から `ORIGIN` か、`FRONTEND`・`CLIENT` と `URL` を含む名前を探し（なければ `FRONTEND_URL`）、`ORIGIN` を含む名前にはサイトのオリジン、それ以外には配信登録時はアプリの URL を入れて Dockerfile の `EXPOSE` の前に `ENV` で書く（既存の Dockerfile には書かず警告） | `portfolio-site/apps/apps.json` の `env`、`<バックエンド>/Dockerfile` |
| 5 | `--build-image` 時のイメージ作成 | `portfolios/docker-images/<スラッグ>-backend.tar`（git 管理外） |
| 6 | 掲載 md の作成。`portfolios/docs/<スラッグ>.md` → README → スラッグの順で情報を使う | `portfolio-site/src/content/portfolios/<スラッグ>.md` |

- 既にあるファイル（コピー先以外）は上書きせず、`warnings` に出す。コピー先 `portfolios/<スラッグ>/` が既にあるとエラー。
- リポジトリ外には書き込まない。

## 開発

```bash
cd portfolios/portfolio-importer
npm test      # python -m unittest
npm run lint  # 構文チェック（python -m compileall）
```

設計: [docs/specs/add-portfolio/](../../docs/specs/add-portfolio/design.md)
