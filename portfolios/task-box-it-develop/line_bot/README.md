# line_bot

「タスク百葉箱」のLINE BOTサーバー（Python / FastAPI）。LINE公式アカウントのWebhookを受け、ユーザー情報の登録・面談予定日の調整・契約の案内・契約者との対話を行う。

`backend/`（Django）とはコードもDBも共有しない独立したアプリ。

## 起動

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python.exe -m alembic upgrade head

# 公開URL（LINEからWebhookを受けるため）。アプリより先に起動しておく
ngrok http 8100

# Webプロセス（Webhookの受信）
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8100
# Celeryのworker（機能の実行・LLM・メッセージの送信）。別のターミナルで動かす。Redisが必要
# Windowsは --pool=solo（既定の prefork は fork を使うため動かない）。本番Linuxは --concurrency=4
.venv\Scripts\celery.exe -A app.celery_app worker --loglevel=info --pool=solo
```

`web` / `worker` / Redis の3つが動いていないと、返信は届かない。Webhookを受け取っても `enqueue` の時点で失敗する。

## Redis の用意

Celeryのブローカーに使う。同梱の `docker-compose.yml`（`redis:7`）で起動する。

```bash
docker compose up -d redis     # 起動（Docker Desktop が動いていること）
docker compose ps              # 状態
docker compose down            # 停止
```

Dockerを使えない場合は Memurai（Windows向けのRedis互換サーバー）や WSL2 の `redis-server` でもよい。

接続先は `.env` の `REDIS_URL`（既定 `redis://localhost:6379/0`）。疎通の確認:

```bash
.venv\Scripts\python.exe -c "from redis import Redis; print(Redis.from_url('redis://localhost:6379/0').ping())"   # True
curl http://localhost:8100/healthz                                                                                  # {"ok":true,"db":true,"redis":true}
```

別のプロジェクトが 6379 番を使っている場合は、そのプロセスを止めずに、DB番号を分ける（`redis://localhost:6379/1`）か、別ポートで起動して `REDIS_URL` を合わせる。

キューの滞留を見たいときは `docker exec -it line-bot-redis redis-cli llen celery`。worker が動いていれば、積まれた分はすぐ 0 に戻る。実行中のタスクは `.venv\Scripts\celery.exe -A app.celery_app inspect active` で確認できる。

**Redisだけ起動してもworkerが無ければ処理されない**（タスクが積まれるだけで、依頼者には待機メッセージしか届かない）。`web` / `worker` / Redis の3つを必ずそろえる。

## 公開URL（ngrok）

LINEのWebhookはHTTPSの公開URLにしか届かない。開発では ngrok で作る。

1. 一度だけ: `ngrok config add-authtoken <トークン>`（**アプリは認証トークンを持たない**）
2. 毎回: `ngrok http 8100` を別ターミナルで起動しておく（アプリより先。閉じるとURLが変わる）
3. `.env` に `USE_NGROK=true`

これで、アプリの起動時に ngrok の公開URLを読み、**LINEのWebhookエンドポイントが自動で設定される**（LINE Developers の画面での貼り替えが不要）。起動すると次のように出る。

```
INFO app.startup ngrokの公開URLを使用します
INFO app.startup ------------------------------------------------------------
INFO app.startup 公開URL              : https://8a1b-203-0-113-5.ngrok-free.app
INFO app.startup Webhook URL          : https://8a1b-203-0-113-5.ngrok-free.app/webhook
INFO app.startup LIFFのエンドポイント : https://8a1b-203-0-113-5.ngrok-free.app/liff
INFO app.startup ngrokの管理画面      : http://127.0.0.1:4040
INFO app.startup ------------------------------------------------------------
INFO app.startup LINEのWebhookエンドポイントを設定しました: https://8a1b-.../webhook
INFO app.startup Webhookの疎通確認に成功しました
```

`http://localhost:8100/healthz` の `public_url` でも現在のURLを確認できる。ngrokの管理画面（`http://127.0.0.1:4040`）では、LINEから届いたリクエストの中身を後から確認できる。

```
USE_NGROK=true  → ngrokのURLを使い、LINEのWebhook設定を書き換える（開発用）
USE_NGROK=false → PUBLIC_BASE_URL をそのまま使い、LINEのAPIを一切呼ばない（本番の既定）
```

注意:

- `USE_NGROK=true` の `.env` には**開発用チャネル**のチャネルアクセストークンだけを置く（本番チャネルのWebhook設定を書き換えないため）。
- ngrok を起動し忘れると、公開URLが取得できずWebhookの設定は更新されない（古い設定のまま。起動ログに警告が出る）。
- アプリは ngrok のトンネルを張らない。`--reload` で再起動してもURLが変わらないようにするため。
- LIFFを使う場合、LIFFアプリ側のエンドポイント（`<公開URL>/liff`）は手動で設定する。起動ログに設定すべきURLが出る。

## そのほかのコマンド

```bash
.venv\Scripts\python.exe -m pytest                                   # テスト
.venv\Scripts\python.exe -m app.cli purge                            # 保持期間を過ぎた履歴の削除（1日1回）
.venv\Scripts\python.exe -m app.cli set_contract <userId> active     # 契約状態の変更
```

セットアップ、環境変数、アーキテクチャ、デプロイ構成、運用の手順は [docs/line-bot.md](../docs/line-bot.md) を参照。仕様は [.kiro/specs/line-bot-server/](../.kiro/specs/line-bot-server/requirements.md)。
