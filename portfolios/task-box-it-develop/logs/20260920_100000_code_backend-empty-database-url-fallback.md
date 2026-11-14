# backend: DATABASE_URL が空文字のとき SQLite にフォールバックする

## 何を

- `backend/config/settings.py` の `DATABASES` を `dj_database_url.config()` から `dj_database_url.parse(os.environ.get("DATABASE_URL") or <sqlite の既定URL>)` に変更した。

## なぜ

- `.env.example` をコピーした `.env` では `DATABASE_URL=`（空文字）になる。`python-dotenv` は空文字をそのまま環境変数に載せ、`dj_database_url.config()` は空文字を「設定あり」とみなして `{}` を返すため、`ENGINE` の無い設定になり `manage.py migrate` が `settings.DATABASES is improperly configured` で失敗していた。
- 空文字を未設定として扱うことで、`.env.example` そのままの状態でも既定の `backend/db.sqlite3` で起動できるようにした。
