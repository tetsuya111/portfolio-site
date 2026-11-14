"""保持期間を過ぎたデータの削除（`purge`）。

会話履歴は最後のやり取りから24時間、処理済みイベントは48時間で消す。
件数だけをログに出し、本文・名前・メールアドレスは出さない。
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from .config import get_settings
from .db import session_scope
from .models import ConversationTurn, ProcessedEvent

logger = logging.getLogger(__name__)


def purge(now: datetime | None = None) -> dict:
    settings = get_settings()
    now = now or datetime.now(timezone.utc)
    history_threshold = now - timedelta(hours=settings.history_retention_hours)
    event_threshold = now - timedelta(hours=settings.event_retention_hours)

    with session_scope() as session:
        # 「最後のやり取り」が期限を過ぎたユーザーの履歴をまとめて消す
        expired_users = session.scalars(
            select(ConversationTurn.line_user_id)
            .group_by(ConversationTurn.line_user_id)
            .having(func.max(ConversationTurn.created_at) < history_threshold)
        ).all()
        turns = 0
        if expired_users:
            turns = session.execute(
                delete(ConversationTurn).where(ConversationTurn.line_user_id.in_(expired_users))
            ).rowcount or 0
        events = session.execute(
            delete(ProcessedEvent).where(ProcessedEvent.created_at < event_threshold)
        ).rowcount or 0

    result = {"users": len(expired_users), "turns": turns, "events": events}
    # 0件でも出す（定期実行が動いていることの確認になる）
    logger.info(
        "保持期間切れの削除: ユーザー %d件 / 履歴 %d件 / イベント %d件 / しきい値 %s",
        result["users"], turns, events, history_threshold.isoformat(),
    )
    return result
