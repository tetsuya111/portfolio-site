# LINE BOTサーバーの雛形・Webhook受信・振り分けを実装（タスク1〜5, 10）

## 何を

`line_bot/` を3つ目のアプリとして追加した（Python / FastAPI）。

- **雛形**: `app/config.py`（環境変数）、`app/db.py`（SQLAlchemy）、`app/messages.py`（依頼者向けの定型文の集約）、`requirements.txt`、`.env.example`、`.gitignore`、`README.md`、`worker.py`（RQのworker）。`GET /healthz` はDBとRedisへの疎通を確認する。
- **データモデル**: `users` / `conversation_turns` / `processed_events`。Alembicの初期マイグレーション（`0001_initial`）で作成できる。契約状態を書き換えるコードはリクエストの処理に存在せず、`python -m app.cli set_contract` だけが変更できる。
- **Webhook**: 生のボディで署名を検証（`hmac.compare_digest`）→ `processed_events` へのINSERTの主キー違反で重複排除 → ジョブ登録 → 200。テキストとpostback以外のイベントは無視する。
- **振り分け**: 機能の判定はpostbackの `data`（`action=register` など）で行い、テキストの先頭文字列では判定しない。すべての返信にクイックリプライを付ける。未契約者のテキストはLLMもジョブも使わずに案内を返す。
- **準備中の機能**: 「面談予定日の調整」は「機能改修中」、「契約する」は `CONTRACT_PAGE_URL` があればリンク、なければ「機能改修中」。

## なぜ

`.kiro/specs/line-bot-server/tasks.md` のタスク1〜5と10。Webhookの即時応答と冪等性、未契約者にLLMを使わせないことが要件の中心。

## 実装で判断したこと

- 開発用DBはSQLite（`DATABASE_URL` 未設定時）。本番はPostgreSQL。`conversation_turns.id` はSQLiteで自動採番されるよう `BigInteger().with_variant(Integer, "sqlite")` にした。
- 返信は `Responder` にまとめ、reply token が使えるうちは reply（通数を消費しない）、なければ Push にフォールバックする。1イベント1通に保つ。
- LINE Messaging API は薄い自前クライアント（httpx）にした。`X-Line-Retry-Key`、403（ブロック済み）は再試行しない、429 は `Retry-After` に従う、5xx/タイムアウトは最大3回の再試行を実装。

## 確認

`python -m pytest` 35件パス（署名の正常/改ざん/なし、冪等性、対象外イベント、unfollowで消さない、postbackの各機能、未契約者でLLMを呼ばない、クイックリプライの内容）。
