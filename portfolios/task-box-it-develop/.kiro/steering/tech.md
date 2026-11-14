---
inclusion: always
---

# 技術スタック

- **バックエンド**: Python + Django + Django REST Framework。詳細・コマンドは [docs/backend.md](../../docs/backend.md)。
- **フロントエンド**: Next.js（App Router）+ React + TypeScript + Tailwind CSS。詳細・コマンドは [docs/frontend.md](../../docs/frontend.md)。
- **LINE BOTサーバー**: Python + FastAPI + SQLAlchemy/Alembic。非同期の処理は Redis + RQ のworkerで行う。詳細・コマンドは [docs/line-bot.md](../../docs/line-bot.md)。
- **認証**: Google認証（IDトークンをバックエンドで検証）+ ステートレスJWT。アクセストークンはフロントのメモリ、リフレッシュトークンは httpOnly Cookie。
- **LLM**: Claude（Anthropic Python SDK）。モデルは環境変数 `LLM_MODEL` で切り替える（既定値 `claude-sonnet-5`）。
- **データベース**: `DATABASE_URL` 環境変数で切り替え。開発環境は sqlite がデフォルト、本番は PostgreSQL を想定。
- **Embedding / RAG**: Voyage AI を使う予定だが未実装（後の追加仕様）。
- **インフラ**: このリポジトリの対象外（別途作成する）。申し送り事項は [docs/backend.md](../../docs/backend.md) にある。
- **構成方針**: `backend/` / `frontend/` / `line_bot/` に分割し、ビルドツールもDBも共有しない。`backend/` と `frontend/` はHTTPで通信し、`line_bot/` は独立したサービスとして動く（ヒアリングサイトへはリンクで案内する）。

## 設計上の方針

- 画面はモダンかつカジュアルに、simple is best。依頼者向けの文言には専門用語を使わない。
- エージェントは「ロールプロンプトを持ち、入力を与えると出力を返す」だけの薄いクラスとし、エージェント同士は直接呼び合わない。受け渡しは常にバックエンドのサービス層が仲介する。
- 依頼者の入力を起点に他のエージェントを呼び出す際は、必ずダイアログでユーザーの許可を取る。
- 機械的に解釈するLLMの出力は、自由文ではなく構造化出力（JSONスキーマ）で受け取る。
- エージェントのプロンプトはコードに埋め込まず、DBで差し替え可能にする。
- APIキーなどの秘密情報は環境変数で渡し、リポジトリにコミットしない。

コマンドや設定の詳細をここに重複して書かず、更新時は必ず [docs/backend.md](../../docs/backend.md) / [docs/frontend.md](../../docs/frontend.md) 側を更新すること。
