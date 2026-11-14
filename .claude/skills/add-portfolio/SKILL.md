---
name: add-portfolio
description: 指定したプロジェクトを portfolios/ に取り込み、フロントエンドの S3 配信登録・バックエンドの Dockerfile とイメージ作成・portfolio-site への掲載までを行う。/add-portfolio <プロジェクトのパス> で明示起動のみ。
disable-model-invocation: true
---

# add-portfolio

引数（`$ARGUMENTS`）で指定したプロジェクトを、ポートフォリオとして追加する。処理の本体は Python 製コマンド [portfolios/portfolio-importer](../../../portfolios/portfolio-importer/README.md) で、このスキルはそれを実行し、結果を確認・仕上げ・報告する。

## 確認のルール

基本は確認せずに進める。次の操作だけは、実行する直前に AskUserQuestion で yes/no を確認する。no なら行わずに続ける。

| 操作 | 理由 |
|---|---|
| `--build-image` を付けた実行（`docker build`） | ベースイメージを外部（Docker Hub）から取得する |
| `npm install`・`npm ci`・`pip install` など、パッケージを取得する操作 | 外部サイトへのアクセス |
| リポジトリ外のファイルの作成・修正・削除 | このプロジェクト以外のディレクトリの操作 |

コピー元がリポジトリ外にあっても、コマンドはコピー元を**読むだけ**なので確認しない。

## 手順

1. **引数の確認**: `$ARGUMENTS` からプロジェクトのパスと、あれば `--slug`・`--site-url`・`--backend-url` を取り出す。パスがなければ、直前の会話・開いているファイルから推定する。推定できなければ理由を報告して終了する。
   - `--site-url` が引数になければ付けない。コマンドが `portfolio-site/infra/parameters.json` の `DomainName` から `https://<ドメイン>` を使う（ファイルがなければ掲載 md の `url` とバックエンドの `ENV` は入らない）。
   - `--backend-url`（フロントエンドから呼ぶバックエンドの URL。https のみ）は引数にあるときだけ付ける。推測で付けない。
2. **取り込み**（イメージは作らない）:
   ```bash
   python portfolios/portfolio-importer/add_portfolio.py <パス> [--slug <スラッグ>] [--site-url <URL>] [--backend-url <URL>]
   ```
   終了コード 1 なら標準エラーの理由を報告して終了する（例: コピー先が既にある → 既に取り込み済みなら `portfolios/<スラッグ>` を指定して再実行してよい）。成功なら標準出力の JSON（`slug`・`projectDir`・`copied`・`frontend`・`backend`・`content`・`warnings`）を読む。
3. **Docker イメージ**: `backend` があり、`warnings` に「CMD」を含む警告がない場合だけ、上の確認ルールで yes/no を確認する。yes なら、対象を `portfolios/<スラッグ>` にして `--build-image` 付きで再実行する（`portfolios/` 配下はコピーせず、既存の生成物も上書きしないので安全）。CMD の警告がある場合は、生成された Dockerfile の起動コマンドを補うよう報告に書く（推測で CMD を書き足さない）。
4. **掲載 md の仕上げ**: `content` が null でなければそのファイルを読み、次だけを直す。
   - プロジェクト内への相対リンク・画像（`./docs/x.md` など）は、サイト上で開けないため、文章に置き換えるか削除する。
   - 見出しが `#` から始まっていれば `##` 以下に下げる。
   - 本文が雛形（「ここにポートフォリオの説明を書く」）のままなら、プロジェクトの README・コードから概要・主な機能・技術構成を書く。
5. **検証**: `portfolio-site/` で `npm test` と `npm run lint` を実行し、出力は失敗箇所だけを確認する（例: `| tail -30`）。失敗したら原因を直す（掲載 md の frontmatter など）。依存が未インストールで実行できない場合は、確認ルールに従う。
6. **作業ログ**: CLAUDE.md の規則に従い `logs/<yyyymmdd_hhMMss>_content_add-portfolio-<スラッグ>.md` に、何を・なぜ取り込んだかを書く。
7. **報告**: 次を箇条書きで示す。コミットはしない（ユーザーに任せる）。
   - 取り込み先（コピーしたか）、作成・更新したファイル
   - フロントエンド: 配信登録したか。しなかった場合はその理由。登録した場合の配信 URL（`<サイトURL>/apps/<スラッグ>/`）と、`apps.json` の `env`（バックエンドの URL を入れた環境変数名。名前は推測のため、ユーザーに確認してもらう）
   - バックエンド: Dockerfile の場所、`ENV` に書いたフロントエンドの URL（`backend.env`）、イメージの tar の場所（作った場合）
   - `warnings` の全件と、ユーザーが手で対応すべきこと

## よくある間違い

| 間違い | 正しい扱い |
|---|---|
| 確認なしで `--build-image` を付ける | 必ず yes/no を確認してから |
| コピー先が既にあるエラーで `portfolios/<スラッグ>` を削除して再実行する | 削除しない。取り込み済みなら `portfolios/<スラッグ>` を指定して再実行する |
| 静的出力できないフロントエンドを `apps.json` に手で登録する | 登録しない（デプロイ全体が止まる）。理由を報告する |
| 既存の掲載 md・Dockerfile を上書きする | 上書きしない。差分が必要なら報告に書く |
