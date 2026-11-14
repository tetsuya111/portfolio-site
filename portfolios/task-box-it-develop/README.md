# タスク百葉箱

「こんなツールがほしい」を、おしゃべりするだけで気軽に相談できる、小規模ツール開発の受付プラットフォーム。

依頼者はAIのヒアリングエージェントと雑談形式で対話しながら要件をまとめ、要件サマリーと見積もりの概算をその場で得られる。確定した要件サマリーは管理者（開発者本人）にメールと管理者画面で届き、以降の面談・契約・開発は管理者がサイトの外で行う。

プロダクトの前提は [.kiro/steering/product.md](.kiro/steering/product.md)、機能の仕様は [.kiro/specs/hearing-chat-site/](.kiro/specs/hearing-chat-site/requirements.md) を参照。

## 構成

| ディレクトリ | 内容 |
| --- | --- |
| [backend/](backend/) | Django REST Framework のAPI（Google認証 + JWT、Claude によるエージェント、要件サマリーの送信・管理） |
| [frontend/](frontend/) | Next.js（App Router）の画面（LP、ログイン、対話画面、管理者画面） |
| [docs/](docs/) | バックエンド / フロントエンドの詳細ドキュメント |
| [.kiro/](.kiro/) | steering（プロジェクトの前提）/ specs（機能ごとの要件・設計・タスク）/ hooks |
| memo/ | 構想メモとエージェントのプロンプト草案 |
| logs/ | 作業ログ |

バックエンドとフロントエンドは独立しており、HTTP経由でのみ通信する。

## 動かし方

前提: Python 3.12、Node.js 24。

```powershell
# バックエンド（http://localhost:8000）
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env          # 値を設定する
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_agents
.\.venv\Scripts\python manage.py runserver

# フロントエンド（http://localhost:3000）
cd frontend
npm install
Copy-Item .env.example .env.local    # 値を設定する
npm run dev
```

必要な外部サービスと、その設定先:

| サービス | 用途 | 設定 |
| --- | --- | --- |
| Google（OAuthクライアントID） | ログイン | `backend/.env` の `GOOGLE_OAUTH_CLIENT_ID` と `frontend/.env.local` の `NEXT_PUBLIC_GOOGLE_CLIENT_ID`（同じ値） |
| Anthropic（APIキー） | エージェントのLLM | `backend/.env` の `ANTHROPIC_API_KEY` |
| メール送信 | 要件サマリーの管理者への通知 | `backend/.env` の `EMAIL_*` と `ADMIN_EMAIL` |

これらが未準備でも、`backend/.env` に `ALLOW_DEV_LOGIN=true` と `LLM_CLIENT_CLASS=agents.demo.DemoLLMClient`、`frontend/.env.local` に `NEXT_PUBLIC_ENABLE_DEV_LOGIN=true` を設定すると、開発用ログインと決まった応答を返すデモのLLMで画面の動きを確認できる（`DEBUG=true` のときのみ）。

環境変数の一覧、テスト、管理者の設定（`set_admin`）などの詳細は [docs/backend.md](docs/backend.md) / [docs/frontend.md](docs/frontend.md) を参照。

## テスト

```powershell
cd backend; .\.venv\Scripts\python manage.py test     # 実際のLLMは呼ばない
cd frontend; npm run lint; npm run test; npm run build
```

## 開発の進め方

新しい機能は、実装より先に `.kiro/specs/<feature-slug>/` に requirements → design → tasks を書く（[.kiro/specs/README.md](.kiro/specs/README.md)）。Claude Code で作業する際の指針は [CLAUDE.md](CLAUDE.md)。
