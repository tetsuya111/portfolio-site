"""保持期間を過ぎた対話履歴の消去。

最後のメッセージから `CONVERSATION_RETENTION_DAYS` 日が過ぎた対話の履歴を消す。消去そのものは
「クリア」と同じ `clear_conversation()` に任せ、処理を2か所に分けない。

対話（1ユーザー1件の入れ物）・確定送信済みの要件サマリー・使用量の記録は消さない。
定期実行は `python manage.py purge_conversations`（詳細は docs/backend.md）。
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Max, Q
from django.utils import timezone

from .models import Conversation
from .services import clear_conversation

logger = logging.getLogger(__name__)


def expired_conversations(now=None):
    """保持期間を過ぎた対話と、判定に使ったしきい値を返す。"""
    now = now or timezone.now()
    threshold = now - timedelta(days=settings.CONVERSATION_RETENTION_DAYS)
    # 実行中の対話は、消去とLLMの応答の保存が競合しないよう対象から外す
    running_since = now - timedelta(seconds=settings.CONVERSATION_LOCK_TIMEOUT_SECONDS)
    queryset = (
        Conversation.objects.annotate(
            last_message_at=Max("messages__created_at"), message_count=Count("messages")
        )
        # メッセージのない対話は消すものがないため対象外
        .filter(last_message_at__isnull=False, last_message_at__lt=threshold)
        .filter(
            Q(processing_started_at__isnull=True) | Q(processing_started_at__lt=running_since)
        )
    )
    return queryset, threshold


def purge_expired_conversations(dry_run=False, now=None):
    """保持期間を過ぎた対話履歴を消す。何度実行しても結果は変わらない。"""
    queryset, threshold = expired_conversations(now)
    conversations = list(queryset)
    messages = sum(conversation.message_count for conversation in conversations)
    if not dry_run:
        for conversation in conversations:
            clear_conversation(conversation)
    # 件数だけを出す。対話の内容やユーザーを特定できる情報はログに残さない
    logger.info(
        "保持期間切れの対話履歴: 対象 %d件 / メッセージ %d件 / しきい値 %s%s",
        len(conversations), messages, threshold.isoformat(), "（dry-run）" if dry_run else "",
    )
    return {
        "conversations": len(conversations),
        "messages": messages,
        "threshold": threshold,
        "dry_run": dry_run,
    }
