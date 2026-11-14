# 非同期処理を RQ から Celery に変更（ブローカーはDockerのRedis）

## 何を

`.kiro/specs/line-bot-server/` の design.md / tasks.md / requirements.md を更新した。

- 非同期の実行基盤を RQ から **Celery** に変更。ブローカーは引き続き Redis で、ローカル開発では **Docker の `redis:7` イメージ**を使う（`line_bot/docker-compose.yml` を追加する想定）。
- `app/celery_app.py`（設定）と `app/tasks.py`（`handle_event` タスク）の構成に変更。`task_acks_late=True` / `task_reject_on_worker_lost=True` とし、実行中にworkerが落ちたタスクは再配送させる（少なくとも1回。二重配送は許容）。
- Windowsでのworker起動は `--pool=solo`（prefork は `os.fork` を使うため動かない）、本番Linuxは prefork + `--concurrency=4` と明記した。
- タスクの送信に失敗した場合は `processed_events` の行を消してから500を返す方針を、リスク表と完了条件に追加した（記録だけ残って処理されない取りこぼしを防ぐ）。
- tasks.md のタスク4を差し替え、ステータスを In Progress に戻した（Celeryへの切り替えは未実装）。

## なぜ

ユーザーの指示による。あわせて、RQのworkerが `os.fork` に依存しWindowsでの開発に追加の工夫が必要だった点、定期実行や再試行を自前で作り込む必要があった点も、Celeryを選ぶ理由として代替案の表に残した。

## 補足

- 一度スレッドプール方式に変更しかけたが、ユーザーの指示で Celery に変更したため、スレッド方式の記述は残していない。
- 実装（`line_bot/` のコード）は未変更。現在は RQ（`app/jobs.py` / `worker.py`）のままで、テストは同期実行のキューで通している。
