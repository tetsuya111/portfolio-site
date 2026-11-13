# portfolio-importer

指定したプロジェクトをポートフォリオとして取り込むコマンド。Claude Code のスキル [/add-portfolio](../../.claude/skills/add-portfolio/SKILL.md) から呼び出す。Python 3.12 の標準ライブラリだけで動く（追加のインストール不要）。

## 使い方

リポジトリのルートで実行する。

```bash
python portfolios/portfolio-importer/add_portfolio.py <プロジェクトのパス> [--slug <スラッグ>] [--site-url <URL>] [--build-image]
```

| 引数 | 内容 |
|---|---|
| `<プロジェクトのパス>` | 取り込むディレクトリ。`portfolios/` 配下ならコピーせずそのまま使う |
| `--slug` | スラッグ（省略時はディレクトリ名から作る）。英小文字・数字・ハイフン。`docs`・`docker-images`・`portfolio-importer` は使えない |
| `--site-url` | ポートフォリオサイトの URL。フロントエンドを配信登録したとき、掲載 md の `url` を `<URL>/apps/<スラッグ>/` にする |
| `--build-image` | `docker build` でバックエンドのイメージを作り `portfolios/docker-images/<スラッグ>-backend.tar` に保存する（ベースイメージを外部から取得する） |

結果は JSON で標準出力に出る。エラー時は理由を標準エラーに出し、終了コード 1 で終わる。

## 行うこと

| 順 | 内容 | 作成・変更するもの |
|---|---|---|
| 1 | プロジェクトのコピー。各階層の `.gitignore` に一致するもの、`.git/`、DB（`*.sqlite`・`*.sqlite3`・`*.db` など）、`.env`・`.env.*`（`.env.example` を除く）、シンボリックリンクはコピーしない | `portfolios/<スラッグ>/` |
| 2 | node 製フロントエンド（`frontend/`・`web/`・`client/`・ルート）の検出。Vite・Astro・`output: "export"` の Next.js だけを配信登録する | `portfolio-site/apps/<スラッグ>/`、`portfolio-site/apps/apps.json`（[配信の仕組み](../../portfolio-site/docs/apps.md)） |
| 3 | バックエンド（`backend/`・`server/`・`api/`・ルート。Python / node）の Dockerfile 生成。起動コマンドは uvicorn の記載・`FastAPI(` の代入・`main.py`・`npm start` から判定する | `<バックエンド>/Dockerfile`、`<バックエンド>/.dockerignore` |
| 4 | `--build-image` 時のイメージ作成 | `portfolios/docker-images/<スラッグ>-backend.tar`（git 管理外） |
| 5 | 掲載 md の作成。`portfolios/docs/<スラッグ>.md` → README → スラッグの順で情報を使う | `portfolio-site/src/content/portfolios/<スラッグ>.md` |

- 既にあるファイル（コピー先以外）は上書きせず、`warnings` に出す。コピー先 `portfolios/<スラッグ>/` が既にあるとエラー。
- リポジトリ外には書き込まない。

## 開発

```bash
cd portfolios/portfolio-importer
npm test      # python -m unittest
npm run lint  # 構文チェック（python -m compileall）
```

設計: [docs/specs/add-portfolio/](../../docs/specs/add-portfolio/design.md)
