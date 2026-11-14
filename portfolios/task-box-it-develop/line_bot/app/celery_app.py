"""Celery の設定。

ブローカーは Redis（ローカルは Docker の `redis:7`、本番はマネージドのもの）。結果は使わないため
保存しない。実行中にworkerが落ちたタスクは再配送させる（少なくとも1回。二重に届くことは許容する）。

worker の起動:
    celery -A app.celery_app worker --loglevel=info --concurrency=4     # Linux（本番）
    celery -A app.celery_app worker --loglevel=info --pool=solo         # Windows（開発）
"""

from celery import Celery

from .config import get_settings


def create_celery() -> Celery:
    settings = get_settings()
    app = Celery("line_bot", broker=settings.redis_url, include=["app.tasks"])
    app.conf.update(
        # 結果は誰も読まないので保存しない（Redisにゴミを残さない）
        task_ignore_result=True,
        task_serializer="json",
        accept_content=["json"],
        # 実行が終わってからackする。workerが落ちたタスクは別のworkerへ再配送される
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        # 1つずつ取り出す（長い処理を1つのworkerが抱え込まないようにする）
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        timezone="Asia/Tokyo",
    )
    return app


celery_app = create_celery()
