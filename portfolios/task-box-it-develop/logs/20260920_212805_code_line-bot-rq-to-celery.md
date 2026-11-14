# LINE BOTサーバーの非同期実行を RQ から Celery に差し替え（タスク4・12）

## 何を

- `app/celery_app.py`（新規）: Celeryの設定。ブローカーは `REDIS_URL`、結果は保存しない（`task_ignore_result`）、JSON直列化、`task_acks_late=True` / `task_reject_on_worker_lost=True`（実行中にworkerが落ちたタスクを再配送）、`worker_prefetch_multiplier=1`。
- `app/tasks.py`（新規）: `line_bot.handle_event` タスクと、Webプロセスから呼ぶ唯一の入口 `dispatch()`。
- `app/main.py`: `enqueue()` を `dispatch()` に変更。**タスクの送信に失敗したら `processed_events` の行を消して500を返す**（`_forget()`）。ヘルスチェックのRedis確認をブローカーへの ping に変更。
- `app/jobs.py` と `worker.py` を削除。`requirements.txt` の `rq` を `celery[redis]` に差し替え。
- `docker-compose.yml`（新規）: ローカル開発用に `redis:7` のみを定義（アプリはvenvのまま動かす）。
- テスト: `InlineQueue` をやめ、`app.main.dispatch` を差し替えて同期実行する fixture にした。`task_always_eager` は使わない（ユーザーの指示）。ブローカー障害時に500を返し記録が残らないことのテストを追加。
- `line_bot/README.md` / `docs/line-bot.md`: Redisの起動を `docker compose up -d redis` に、workerを `celery -A app.celery_app worker`（Windowsは `--pool=solo`、本番Linuxは `--concurrency=4`）に更新。「Redisだけ起動してもworkerが無ければ処理されない」ことを明記。

## なぜ

ユーザーの指示（Celery + DockerのRedis）による。あわせて、以前から残っていた「ブローカーへ渡せないまま処理済みとして記録され、イベントが二度と処理されない」穴を塞いだ。

## 確認

- `python -m pytest` 36件パス（新規1件を含む）。
- タスクの登録（`line_bot.handle_event`）と設定値を確認。
- Redis未起動の状態でWebhookを叩き、**500が返り `processed_events` に記録が残らない**ことを確認。
- Docker Desktop が停止しているため、実際にRedis + workerを起動しての疎通は未実施（tasks.md の未完了項目として残している）。
