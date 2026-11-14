"""Celery のタスク。

Webプロセスからは `dispatch()` だけを呼ぶ。引数はJSONにできる素の辞書に限る
（Celeryは本番でJSONに直列化するため、日付やモデルのインスタンスを渡さない）。
"""

import logging

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="line_bot.handle_event")
def handle_event(event: dict) -> None:
    # 循環importを避けるため、ここで読み込む
    from .features.router import handle_event as run

    run(event)


def dispatch(event: dict) -> None:
    """1件のイベントの処理をworkerへ渡す。テストではこの関数を差し替える。"""
    handle_event.delay(event)
