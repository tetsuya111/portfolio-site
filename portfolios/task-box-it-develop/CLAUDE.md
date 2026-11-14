# CLAUDE.md

このファイルは、このリポジトリで作業する Claude Code (claude.ai/code) 向けのガイドです。

**このファイルおよび今後の追記・更新はすべて日本語で記述すること。**

## プロジェクト概要

「タスク百葉箱」— 小規模ツール開発を気軽に依頼できる受付プラットフォーム。依頼者がAIチャットボットと雑談形式で対話しながら要件サマリーと見積もりの概算を作成し、まとまった内容を管理者（開発者本人）へ送信する。プロダクトの前提は [.kiro/steering/product.md](.kiro/steering/product.md) を参照。

## プロジェクト構成

以下の3つの独立したアプリからなるモノレポ。相互に共通のビルドツールを持たず、HTTPまたはリンクの案内でのみやり取りする。

- `backend/` — Django REST Framework による API（Google認証 + JWT、LLMはデフォルトで Claude）
- `frontend/` — Next.js（App Router, TypeScript）による React フロントエンド
- `line_bot/` — LINE公式アカウントの窓口（Python / FastAPI + Redis/RQ）。`backend/` とはコードもDBも共有しない

このほかに、`memo/`（構想メモとエージェントのプロンプト草案。`memo/雑多な/ITビジネス/タスク百葉箱/` 配下がこのプロダクトの一次情報）と `.kiro/`（後述）がある。

実装済みの機能は [.kiro/specs/hearing-chat-site/](.kiro/specs/hearing-chat-site/requirements.md)（ヒアリングチャットサイト）。RAG（Embedding は Voyage AI を予定）は未実装で、後の追加仕様とする。

技術選定は [.kiro/steering/tech.md](.kiro/steering/tech.md)、ディレクトリ構成は [.kiro/steering/structure.md](.kiro/steering/structure.md) を参照。

## ドキュメント一覧

詳細は各ドキュメントに一本化し、このファイルは索引とする。新しい詳細情報を追記する際は、このファイルに直接書かず該当ドキュメントを更新すること。

- [docs/backend.md](docs/backend.md) — バックエンドのセットアップ、コマンド、環境変数、アーキテクチャ、インフラへの申し送り事項
- [docs/frontend.md](docs/frontend.md) — フロントエンドのセットアップ、コマンド、環境変数、アーキテクチャ
- [docs/line-bot.md](docs/line-bot.md) — LINE BOTサーバーのセットアップ、コマンド、環境変数、アーキテクチャ、デプロイ構成、運用手順
- [docs/line-bot-io.md](docs/line-bot-io.md) — LINE BOT の入出力の対応（どの入力に何を返すか）。返信の文言や振り分けを変えたときは合わせて更新する

## 開発ワークフロー（`.kiro/`）

AWS Kiroの Steering / Specs / Agent Hooks の考え方を、このリポジトリでは `.kiro/` 配下 + Claude Code本来のhooks機構で再現している。

- [.kiro/steering/](.kiro/steering/) — 常時参照される永続的なプロジェクトコンテキスト（product.md / tech.md / structure.md）。新しいセッションでもプロダクトの前提を把握できるようにする。
- [.kiro/specs/](.kiro/specs/README.md) — 機能ごとの requirements.md → design.md → tasks.md。新機能に着手する際は実装より先にここへ仕様を書く。
- [.kiro/hooks/](.kiro/hooks/README.md) — イベント駆動の自動化の一覧。実体は `.claude/settings.json` のhooks設定（`.claude/settings.json` は未作成）。

`memo/` は草案置き場であり、仕様として確定した内容は `.kiro/specs/` / `.kiro/steering/` に反映する。両者が食い違う場合は `.kiro/` 側を正とする。

## エージェントのプロンプトを扱う際の注意

このプロダクトの中核は、エージェントのプロンプト（ヒアリングbot、要件サマリー作成、相場見積もり、自分見積もり）である。草案は `memo/` 配下、アプリの初期値は `backend/agents/seed_prompts/`、稼働中の値はDB（Djangoの管理サイトで編集）にある。`seed_prompts/` を編集しても既存のDBには反映されない。

- 要件サマリーの項目（目的 / ほしい機能 / 期間のレンジ / 予算のレンジ / ゴール（最低基準） / セキュリティ）は全エージェントで共通。変更する際はすべてのプロンプトと [.kiro/steering/product.md](.kiro/steering/product.md) を揃えること。
- 依頼者はITに疎い非エンジニアを想定している。依頼者向けの文言・UIでは専門用語を避け、情報量を最小限にする。
- チャットボットが他のエージェントを自動で呼び出す際は、必ずダイアログでユーザーの許可を取る仕様とする。

## Issueの作成

GitHubでissueを作成する場合は以下に従う（現時点ではGitリポジトリ・issueテンプレートともに未作成）。

- 1つのissueには1つの要件のみを記載する。[.kiro/specs/](.kiro/specs/README.md) と同じ粒度（1機能・1要件 = 1スペック）で作成し、複数の要件をまとめて1つのissueに書かないこと。
- 機能要望のissueには、対象となる `.kiro/specs/<feature-slug>/` のslugを明記する（新規提案なら提案するslug、既存specの変更ならそのslug）。issueの内容がそのままrequirements.mdの元になる想定で書く。

## 作業ログ

- 以下のいずれかを行った場合は、`logs/`以下に「何を・なぜ行ったか」を簡潔に記録すること。
  - 要件定義・設計ドキュメント（`.kiro/specs/` 配下の `requirements.md` / `design.md` / `tasks.md` など）や `.kiro/steering/` の新規作成・修正
  - エージェントのプロンプト（`memo/` 配下の草案を含む）の新規作成・修正
  - プロジェクトのコード・設定への修正（`backend/` / `frontend/` 配下のファイル変更全般）
- ログは修正内容ごとに1ファイルを作成する。1つのファイルに複数の修正内容を混在させないこと。
- ファイル名は `logs/<yyyymmdd_hhMMss>_<種別>_<内容がわかる名前>.md` とし、ファイル名だけで実施日時・修正の種類・内容が判別できるようにする（先頭に日時を置くことで、ディレクトリの一覧表示が時系列順になる）（例: 仕様関連なら `20260917_143012_spec_hearing-chat-requirements.md`、CLAUDE.md自体の修正なら `20260917_090015_claude-md_project-adaptation.md` など）。日時は記録作成時点のローカル時刻とする。
- ログファイルは必ずMarkdown形式（`.md`）で作成する。
- 日々の作業内容を後から追跡できるようにするための記録であり、コミットメッセージやPR説明の代わりにはしない（両方に残す）。

## トークン使用量の節約

Claude Codeとのやり取りではコンテキスト消費（トークン使用量）を最小限に抑えることを常に意識する。

- ファイルを読み込む際は必要最小限のファイル・範囲のみ読み込むこと（無関係なファイルは開かない、大きなファイルは該当箇所のみ`offset`/`limit`で読む）。
- 直前の操作結果や会話内で既に把握できている内容を、確認目的で再度読み込まないこと（例: Edit/Write直後に同じファイルを読み直さない）。
- コードベース全体を対象とした調査では、いきなり多数のファイルを開かず、Grep/Globで対象を絞り込んでから必要なファイルだけを読むこと。
- ビルドログ・テスト結果など出力が長大になりうるコマンドは、フィルタリングして必要な部分のみを確認すること。
- ファイルの一部を変更する場合はWriteによる全文書き換えではなく、Editによる差分編集を優先すること。
- 広範囲・多段階の調査はサブエージェントに委譲し、詳細な探索結果ではなく要約のみをメインの会話コンテキストに持ち込むこと。
- 同じ内容を複数のドキュメントに重複して書かない（単一情報源の原則）。

## 横断的な注意点

- リポジトリ内の `README.md`（ルート、`backend/`、`frontend/` などすべて）は日本語で記載すること。
- `memo/` 配下は日本語のファイル名（macOS由来のNFD形式）を含む。Windowsのシェル出力では文字化けすることがあるため、内容を確認する際はUTF-8を明示して読むこと。
- LLM のAPIキーなどの秘密情報は環境変数で渡し、コミットしない。バックエンドとフロントエンドはそれぞれ独立した `.gitignore` / `.env.example` を持つ。環境依存の設定を追加する際は両方を確認すること。
- ローカルでのクロスオリジンリクエスト（既定は `localhost:3000` ↔ `localhost:8000`）を機能させるため、バックエンドの `CORS_ALLOWED_ORIGINS` とフロントエンドの `NEXT_PUBLIC_API_BASE_URL` は整合性を保つこと。
- 同じPCで別プロジェクト（community_sns）の開発サーバーが 8000 / 3000 番を使っていることがある。Windowsでは同じポートで二重に起動できてしまい、別プロジェクトの応答が返ってくるため、その場合は 8001 / 3001 番など別のポートで起動し、上記の2つの設定を合わせること。起動中の他プロジェクトのプロセスは止めないこと。
- バックエンドのテストは実際のLLMを呼ばない（偽のクライアントに差し替える）。実際のLLMでの確認は、費用がかかるためユーザーの了承を得てから行うこと。
