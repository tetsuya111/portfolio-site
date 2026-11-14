"""LLMの呼び出し回数の上限（1ユーザー・1日、日本時間）。"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import get_settings
from .models import User

JST = ZoneInfo("Asia/Tokyo")

logger = logging.getLogger(__name__)


def today() -> "datetime.date":
    return datetime.now(JST).date()


def consume(session, user: User) -> bool:
    """呼び出しを1回数える。上限に達していれば False を返し、数えない。"""
    limit = get_settings().daily_llm_call_limit
    current = today()
    if user.llm_calls_date != current:
        # 日付が変わったら数え直す
        user.llm_calls_date = current
        user.daily_llm_calls = 0
    if user.daily_llm_calls >= limit:
        logger.info("LLMの上限に達しました: user=%s", user.line_user_id)
        return False
    user.daily_llm_calls += 1
    session.add(user)
    return True
