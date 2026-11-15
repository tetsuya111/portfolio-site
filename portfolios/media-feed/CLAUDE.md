# CLAUDE.md

このファイルは、このリポジトリで作業する Claude Code (claude.ai/code) 向けのガイドです。

**このファイルおよび今後の追記・更新はすべて日本語で記述すること。**

## プロジェクト概要

複数のアダルト動画・画像サイトからバッチでコンテンツを収集し、短尺フィード形式で閲覧できるWebアプリケーション。収集したコンテンツをまとめた記事を作成でき、記事一覧は埋め込み用HTML（ブログパーツ）として外部ブログに貼り付けられる。プロダクトの前提は [.kiro/steering/product.md](.kiro/steering/product.md) を参照。

## プロジェクト構成

バックエンドとフロントエンドの2つからなる。フロントエンドはAPIを相対パス `/api/...` で呼び、Next.js の rewrite がバックエンドへ転送する。

- `backend/` — Django REST Framework による API（JWT認証、SQLite、メディア配信）。収集バッチ（`backend/tools/`）も同じDjangoプロジェクトに同梱されている
- `frontend/` — Next.js（App Router, TypeScript）+ MUI による React フロントエンド

技術選定は [.kiro/steering/tech.md](.kiro/steering/tech.md)、ディレクトリ構成は [.kiro/steering/structure.md](.kiro/steering/structure.md) を参照。

## ドキュメント一覧

詳細は各ドキュメントに一本化し、このファイルは索引とする。新しい詳細情報を追記する際は、このファイルに直接書かず該当ドキュメントを更新すること。

- [readme.md](readme.md) — リポジトリ全体の概要と起動方法
- [backend/readme.md](backend/readme.md) — バックエンドの起動、データモデル一覧、APIエンドポイント一覧、依存ライブラリ
- [backend/tools/readme.md](backend/tools/readme.md) — 収集・加工バッチの一覧、各コマンドの引数、必要な環境変数と外部ツール
- [frontend/readme.md](frontend/readme.md) — フロントエンドの起動、画面一覧、FeedPlayerの操作方法、APIクライアント

## 起動

```bash
bash start.sh              # バックエンド (:8000) とフロントエンド (:3000) をまとめて起動
```

個別に起動する場合や別マシンのバックエンドに接続する場合は各readmeを参照。フロントエンドはすべて相対パスでAPIを呼ぶため、別デバイスから `http://<サーバーIP>:3000` でアクセスできる。

## 開発ワークフロー（`.kiro/`）

AWS Kiroの Steering / Specs / Agent Hooks の考え方を、このリポジトリでは `.kiro/` 配下 + Claude Code本来のhooks機構で再現している。

- [.kiro/steering/](.kiro/steering/) — 常時参照される永続的なプロジェクトコンテキスト（product.md / tech.md / structure.md）。新しいセッションでもプロダクトの前提を把握できるようにする。
- [.kiro/specs/](.kiro/specs/README.md) — 機能ごとの requirements.md → design.md → tasks.md。新機能に着手する際は実装より先にここへ仕様を書く。
- [.kiro/hooks/](.kiro/hooks/README.md) — イベント駆動の自動化の一覧。実体は `.claude/settings.json` のhooks設定（`.claude/settings.json` は未作成）。

作成済みのspecは [.kiro/specs/video-playback-performance/](.kiro/specs/video-playback-performance/requirements.md)（フィードの動画再生の遅さの改善。requirements まで作成済み、design / tasks は未作成）。それ以外の既存機能はspecを作らずに実装されているため、仕様の一次情報は各readmeと `.kiro/steering/` にある。readmeと実装が食い違う場合は実装を正とし、気づいた時点でreadmeを直すこと。

## コンテンツとバッチを扱う際の注意

- `Content.id` は `path + link + title` のSHA256先頭32文字で、モデルの `save()` が自動採番する。手動でIDを組み立てないこと。
- メディアの実体は「ローカル（`backend/media/`）」「S3（`path` が `s3://` で始まる）」「外部URL（`link`）」の3通りがある。配信処理を変更する際は3通りすべてを考慮すること。
- フィードの表示順は `calc_series_weight`（`Series.weight` を再計算）→ `make_series_queue`（`SeriesQueueItem` を再構築）の順に実行して決まる。片方だけ実行すると整合しない。
- 収集バッチは外部サイトのHTML構造やAPIに依存している。動かなくなった場合はまず収集元の変更を疑う。
- 収集バッチ・S3移行・記事生成は外部サービスに実リクエストを送り、費用やダウンロードが発生する。ユーザーの了承を得てから実行すること。確認だけなら `--dry-run` があるコマンドはそれを使う。
- `delete_image_contents` や `split_video_as_short`（元コンテンツを削除して差し替える）のような破壊的なバッチは、実行前に必ず確認を取ること。

## Issueの作成

GitHubでissueを作成する場合は以下に従う。

- 1つのissueには1つの要件のみを記載する。[.kiro/specs/](.kiro/specs/README.md) と同じ粒度（1機能・1要件 = 1スペック）で作成し、複数の要件をまとめて1つのissueに書かないこと。
- 機能要望のissueには、対象となる `.kiro/specs/<feature-slug>/` のslugを明記する（新規提案なら提案するslug、既存specの変更ならそのslug）。issueの内容がそのままrequirements.mdの元になる想定で書く。

## 作業ログ

- 以下のいずれかを行った場合は、`logs/`以下に「何を・なぜ行ったか」を簡潔に記録すること。
  - 要件定義・設計ドキュメント（`.kiro/specs/` 配下の `requirements.md` / `design.md` / `tasks.md` など）や `.kiro/steering/` の新規作成・修正
  - プロジェクトのコード・設定への修正（`backend/` / `frontend/` 配下のファイル変更全般）
  - 各 `readme.md` / `CLAUDE.md` の修正
- ログは修正内容ごとに1ファイルを作成する。1つのファイルに複数の修正内容を混在させないこと。
- ファイル名は `logs/<yyyymmdd_hhMMss>_<種別>_<内容がわかる名前>.md` とし、ファイル名だけで実施日時・修正の種類・内容が判別できるようにする（先頭に日時を置くことで、ディレクトリの一覧表示が時系列順になる）（例: 仕様関連なら `20260920_143012_spec_age-verification-requirements.md`、CLAUDE.md自体の修正なら `20260920_090015_claude-md_project-adaptation.md` など）。日時は記録作成時点のローカル時刻とする。
- ログファイルは必ずMarkdown形式（`.md`）で作成する。
- 日々の作業内容を後から追跡できるようにするための記録であり、コミットメッセージやPR説明の代わりにはしない（両方に残す）。

## トークン使用量の節約

Claude Codeとのやり取りではコンテキスト消費（トークン使用量）を最小限に抑えることを常に意識する。

- ファイルを読み込む際は必要最小限のファイル・範囲のみ読み込むこと（無関係なファイルは開かない、大きなファイルは該当箇所のみ`offset`/`limit`で読む）。`backend/api/views.py` のように800行規模のファイルは全文を読まない。
- 直前の操作結果や会話内で既に把握できている内容を、確認目的で再度読み込まないこと（例: Edit/Write直後に同じファイルを読み直さない）。
- コードベース全体を対象とした調査では、いきなり多数のファイルを開かず、Grep/Globで対象を絞り込んでから必要なファイルだけを読むこと。
- ビルドログ・テスト結果・バッチの出力など長大になりうるコマンドは、フィルタリングして必要な部分のみを確認すること。`backend/logs/access.log` や `package-lock.json` / `yarn.lock` は原則開かない。
- ファイルの一部を変更する場合はWriteによる全文書き換えではなく、Editによる差分編集を優先すること。
- 広範囲・多段階の調査はサブエージェントに委譲し、詳細な探索結果ではなく要約のみをメインの会話コンテキストに持ち込むこと。
- 同じ内容を複数のドキュメントに重複して書かない（単一情報源の原則）。

## 横断的な注意点

- リポジトリ内の `readme.md`（ルート、`backend/`、`backend/tools/`、`frontend/`）は日本語で記載すること。ファイル名は小文字の `readme.md` で統一されている。
- **秘密情報**: バックエンドとバッチの環境変数は `backend/.env` に置き、`settings.py` が `load_dotenv()` で読み込む。秘密情報をコードに直書きしないこと。キーを追加したら [backend/.env.example](backend/.env.example) と [.kiro/steering/tech.md](.kiro/steering/tech.md) の表も更新する。なお、過去に直書きされていた鍵はgit履歴と `backend/tools/set_env.bat` に残っており、ローテーションは未対応（[.kiro/steering/tech.md](.kiro/steering/tech.md) の「本番公開前の未対応事項」を参照）。
- 現状の設定は開発用のまま（`DEBUG = True` / `SECRET_KEY` が既定のプレースホルダ / `ALLOWED_HOSTS = ['*']` / `CORS_ALLOW_ALL_ORIGINS = True`）。公開に関わる変更を行う際はこれらを併せて確認すること。
- APIのパスは末尾スラッシュ必須（`trailingSlash: true` と rewrite ルール `/api/:path*/`）。エンドポイントを追加する際は `backend/api/urls.py` と呼び出し側の両方で末尾スラッシュを揃えること。
- ユーザーのPKは `username`（JWTのクレームも `username`）。`id` 前提のコードを書かないこと。
- ブログパーツを外部サイトに埋め込めるよう、`X-Frame-Options` を無効化し CSP の `frame-ancestors` で許可元を制御している（[frontend/next.config.ts](frontend/next.config.ts)）。ヘッダー設定を変更する際は埋め込みが壊れないか確認すること。
- Turnstile は `NEXT_PUBLIC_TURNSTILE_ENABLED=false` で無効化できる。ローカルで検証ダイアログが邪魔な場合はこれを使う。
- 同じPCで別プロジェクトの開発サーバーが 8000 / 3000 番を使っていることがある。Windowsでは同じポートで二重に起動できてしまい、別プロジェクトの応答が返ってくるため、その場合は 8001 / 3001 番など別のポートで起動し、`BACKEND_URL` を合わせること。起動中の他プロジェクトのプロセスは止めないこと。
- `pyppeteer` / `playwright` / `ffmpeg` / `yt-dlp` はシステム側のインストールが必要。前提は [backend/tools/readme.md](backend/tools/readme.md) を参照。
- `backend/media/`、`db.sqlite3`、`frontend/.next/` は gitignore 対象。生成物をコミットしないこと。
