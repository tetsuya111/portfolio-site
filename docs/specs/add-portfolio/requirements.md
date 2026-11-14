# 要件定義: 指定プロジェクトをポートフォリオとして追加するスキル

元の要望: [memo/add_portfolio_to_portfolio-site.md](../../../memo/add_portfolio_to_portfolio-site.md)

## 前提と仮定

無人実行のため、要望メモ・既存コードから次のとおり判断した。覆したい場合はこの節を起点に修正する。

| # | 仮定 | 根拠 |
|---|---|---|
| A1 | 成果物は Claude Code のプロジェクトスキル `.claude/skills/add-portfolio/` と、スキルから呼ぶ Python 製コマンド（`portfolios/portfolio-importer/`）。Python は標準ライブラリだけで書く | メモの「pythonで作成」「必要な場合はバッチを作成しスキルから呼び出す」。外部パッケージの取得は確認が必要な操作のため、依存を持たない |
| A2 | 「指定したプロジェクト」はローカルのディレクトリパスで指定する | メモにリモート取得の記述がなく、外部アクセスは確認が必要なため |
| A3 | フロントエンドの配信先は既存サイトと同じ S3 バケット・CloudFront の `/apps/<スラッグ>/` 配下とする。CloudFormation はローカルファイルを読めないため、「CloudFormation から読み込む」は、テンプレートで定義した CodeBuild（buildspec）が管理ファイルを読んでビルド・配置することで実現する | 既存の `portfolio-site/infra/template.yaml` は1バケット1ディストリビューション構成で、デプロイは CodeBuild の `s3 sync dist` が行っている |
| A4 | S3 で配信できるのは静的ファイルを出力できるフロントエンドだけ。Vite・Astro・`output: "export"` を設定した Next.js を対象とし、それ以外（サーバー機能が必要な Next.js など）は配信登録をせず警告する | S3 は静的配信のみ。ビルドできないアプリを登録するとサイト全体のデプロイが止まるため |
| A5 | Docker イメージは `docker save` した tar を `portfolios/docker-images/<スラッグ>-backend.tar` に置き、git の管理対象にしない（同ディレクトリに `.gitignore` を置く） | イメージは数百MBになりうり、git で扱うのに向かない |
| A6 | `docker build` はベースイメージを外部から取得するため、スキルは実行前にユーザーへ確認する。コマンドは明示オプション指定時のみイメージを作る | メモの「外部のサイトにアクセスする場合は確認」 |
| A7 | ポートフォリオの URL は、サイトの URL（`--site-url`）が与えられ、かつフロントエンドを配信登録した場合だけ `<サイトURL>/apps/<スラッグ>/` を入れる。リポジトリにサイトのドメインの記載がないため、未指定なら URL を入れない | `astro.config.mjs` に `site` がなく、ドメインは CloudFormation のパラメーターでのみ決まる |
| A8 | 既存の `portfolios/<スラッグ>/` や `portfolio-site/src/content/portfolios/<スラッグ>.md` は上書きしない | 手で書き足した内容を消さないため |

## 背景・課題

ほかの場所で作ったプロジェクトをポートフォリオサイトに載せるには、コピー・不要ファイルの除外・フロントエンドの配信設定・バックエンドのコンテナ化・紹介ページの作成を毎回手作業で行う必要があり、手順の抜けや秘密情報の混入が起きやすい。

## ゴール

- プロジェクトのパスを1つ指定するだけで、`portfolios/` へのコピー、配信・コンテナ化の準備、サイトへの掲載までが終わる。

## Non-Goals（やらないこと）

- Docker イメージのレジストリへの push や、VPS 上での起動・デプロイ
- 静的出力できないフロントエンドを配信できるようにする改修
- リモートリポジトリ（GitHub URL など）からの取得
- 掲載後のポートフォリオ本文の自動的な推敲（スキル内で Claude が手直しする）

## 成功指標

- `portfolios/spotify-billboard-playlist` を指定して実行すると、コピーなしで Dockerfile 生成とポートフォリオ md 作成が終わり、フロントエンドは「静的出力不可」として配信登録されない。
- 実行後も `portfolio-site` の `npm test`・`npm run lint` が成功する。

## ユーザーストーリー

- As a サイトの持ち主, I want 作ったプロジェクトのパスを指定してスキルを実行したい, so that 手作業なしでポートフォリオに追加できる。

## 機能要件（受け入れ基準）

### プロジェクトのコピー

- **R1-1**: WHEN `portfolios/` 外のディレクトリが指定された, THE SYSTEM SHALL その内容を `portfolios/<スラッグ>/` にコピーする。
- **R1-2**: WHEN `portfolios/` 配下のディレクトリが指定された, THE SYSTEM SHALL コピーせず、そのプロジェクトをそのまま使う。
- **R1-3**: THE SYSTEM SHALL 指定プロジェクト内の `.gitignore`（各階層のもの）に一致するファイル・ディレクトリをコピーしない。
- **R1-4**: THE SYSTEM SHALL 非初期データ（`*.sqlite`・`*.sqlite3`・`*.db` とその付随ファイル）、`.git/`、依存・キャッシュ（`node_modules/`・`.venv/`・`venv/`・`__pycache__/`・`*.pyc`）、秘密情報（`.env`・`.env.*`（`.env.example` を除く）・`*.pem`・`*.key`・`*.p12`・`*.pfx`・`.npmrc`・`credentials*.json`）、シンボリックリンクをコピーしない。
- **R1-5**: IF コピー先 `portfolios/<スラッグ>/` が既に存在する, THEN THE SYSTEM SHALL 何もコピーせずエラー終了する。
- **R1-6**: IF 指定パスがディレクトリでない、リポジトリ自体を含む、またはリポジトリ内の `portfolios/` 外にある, THEN THE SYSTEM SHALL エラー終了する。
- **R1-7**: THE SYSTEM SHALL スラッグを指定ディレクトリ名から英小文字 kebab-case で作り、オプションで上書きできるようにする。スラッグが `^[a-z0-9]+(?:-[a-z0-9]+)*$` に合わない、または予約名（`docs`・`docker-images`・`portfolio-importer`）の場合はエラー終了する。

### フロントエンド

- **R2-1**: WHEN プロジェクトに静的出力できる node 製フロントエンドがある, THE SYSTEM SHALL そのソースを `portfolio-site/apps/<スラッグ>/` にコピーし、配信の管理ファイル `portfolio-site/apps/apps.json` に登録する。
- **R2-2**: WHEN node 製フロントエンドが静的出力できない（または判定できない）, THE SYSTEM SHALL 配信登録せず、理由を警告として出力する。
- **R2-3**: WHILE 本番デプロイのビルド中, THE SYSTEM SHALL `apps.json` に登録された各アプリをビルドし、成果物をサイトの `/apps/<スラッグ>/` として S3 に配置する。
- **R2-4**: IF `apps.json` の内容が不正（スラッグ・出力先・引数の形式違反、重複）, THEN THE SYSTEM SHALL ビルドを失敗させ、デプロイしない。

### バックエンド

- **R3-1**: WHEN プロジェクトに Python または node 製のバックエンドがある, THE SYSTEM SHALL そのディレクトリに `Dockerfile` と `.dockerignore` を作成する（既存のものは上書きしない）。
- **R3-2**: IF 起動コマンドを判定できない, THEN THE SYSTEM SHALL 起動コマンドを編集するよう促すコメント付きの `Dockerfile` を作り、イメージは作らず警告する。
- **R3-3**: WHEN イメージ作成が指定された, THE SYSTEM SHALL `docker` コマンドでイメージを作り、`portfolios/docker-images/<スラッグ>-backend.tar` に保存する。

### サイトへの掲載

- **R4-1**: THE SYSTEM SHALL `portfolio-site/src/content/portfolios/<スラッグ>.md` を、サイトのスキーマ（`title` 必須、`tags`、`url`、`date`）に合う形で作成する。
- **R4-2**: WHEN `portfolios/docs/<スラッグ>.md` がある, THE SYSTEM SHALL そのタイトル・タグ・本文を使う。ない場合は README の見出しと本文、検出した技術をタグに使う。
- **R4-3**: WHEN サイト URL が指定され、フロントエンドを配信登録した, THE SYSTEM SHALL `url` に `<サイトURL>/apps/<スラッグ>/` を入れる。http/https 以外の URL は入れない。（サイト URL 未指定時の扱いは [add-portfolio-relative-url](../add-portfolio-relative-url/requirements.md) の R1-1〜R1-3 で変更: 配信登録時は `/apps/<スラッグ>/` を入れる）
- **R4-4**: IF 掲載用 md が既に存在する, THEN THE SYSTEM SHALL 上書きせず警告する。

### スキル

- **R5-1**: THE SYSTEM SHALL `/add-portfolio <パス>` で起動し、コマンドの実行・結果の報告・掲載本文の手直しを行うスキルを提供する。
- **R5-2**: THE SYSTEM SHALL リポジトリ外へのファイル書き込みと外部アクセス（`docker build`・パッケージ取得）を、実行直前にユーザーへ確認する。それ以外は確認しない。

## 非機能要件

- **N1**: コマンドはリポジトリ外にファイルを書き込まない（コピー元は読むだけ）。
- **N2**: Python 3.12 標準ライブラリのみで動き、Windows・Linux で動作する。
- **N3**: コマンドは結果を JSON で標準出力に出し、エラー時は終了コード 1 と理由を標準エラーに出す。
