# line_bot: 環境変数が空文字のときに既定値へフォールバックするよう修正

## 何が起きていたか

LINEからのWebhookは届いていたが、500で失敗していた。

```
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from string ''
```

`.env.example` をコピーした `.env` は `DATABASE_URL=`（空文字）になる。`python-dotenv` は空文字をそのまま環境変数に載せるため、`os.environ.get("DATABASE_URL", <既定値>)` は「設定あり（空文字）」とみなして既定値を使わず、SQLAlchemy がURLを解析できずに落ちていた。

`backend/` で同じ問題を修正済み（`logs/20260920_100000_code_backend-empty-database-url-fallback.md`）だが、`line_bot/` に同じ考慮が入っていなかった。

## 直したこと

`app/config.py` に `_str(name, default)` を追加し、**空文字・空白のみの値を「未設定」として扱う**ようにした。あわせて前後の空白を落とすため、トークンを貼り付けたときの余分な空白で通信が壊れることもなくなる。

適用した設定: `LINE_CHANNEL_SECRET` / `LINE_CHANNEL_ACCESS_TOKEN` / `LIFF_ID` / `DATABASE_URL` / `REDIS_URL` / `ANTHROPIC_API_KEY` / `LLM_MODEL` / `LLM_CLIENT_CLASS` / `CONTRACT_PAGE_URL` / `HEARING_SITE_URL` / `PUBLIC_BASE_URL` / `NGROK_API_URL` / `NGROK_TUNNEL_NAME` / `ENVIRONMENT` / `DIALOGUE_PROMPT_FILE`。

`tests/test_config.py` を追加（空の `DATABASE_URL` / `REDIS_URL` / `LLM_MODEL` が既定値になること、前後の空白が落ちること）。

## 確認

- `python -m pytest` 61件パス（新規4件）。
- 実際の `.env` を読んだ状態で、`database_url` が `sqlite:///line_bot/line_bot.sqlite3` に解決され、テーブル（users / conversation_turns / processed_events）が存在し、Redisにも接続できることを確認。
