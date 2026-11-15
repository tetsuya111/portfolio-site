# Hooks（イベント駆動の自動化）

KiroのAgent Hooksに相当する「特定のイベントで自動的にエージェントの作業を走らせる」仕組みを、Claude Code本来のhooks機構（`.claude/settings.json` の `hooks` 設定）で実装する。設定の実体は `.claude/settings.json` に一本化し、ここには「何が・いつ・なぜ」動くかの一覧だけを記載する（設定内容そのものを重複して書かない）。

## 現在設定されているhooks

現時点では未設定（`.claude/settings.json` も未作成）。

| イベント | 対象 | 動作 | 目的 |
| --- | --- | --- | --- |
| （なし） | | | |

## 追加の候補

- PostToolUse (Edit/Write) — `frontend/**/*.{ts,tsx}` を編集したら `npm run lint` を対象ファイルに実行する
- PostToolUse (Edit/Write) — `backend/api/models.py` を編集したら `python manage.py makemigrations --check` で未作成のマイグレーションを検知する

新しいhookを追加・変更する場合は `.claude/settings.json` を更新し、このテーブルも合わせて更新すること。
