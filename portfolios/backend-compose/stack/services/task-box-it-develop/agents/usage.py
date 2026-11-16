"""1ユーザーあたり1日ごとの使用量（トークン数）の記録と上限の判定。

管理者は上限の対象外（無制限）とする。使用量の記録は、管理者でも依頼者と同じように行う。
"""

from django.conf import settings
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework import status

from config.exceptions import ApiError

from .models import UsageRecord


def record_usage(user, agent_key, purpose, result):
    usage = result.usage
    return UsageRecord.objects.create(
        user=user,
        # TIME_ZONE が Asia/Tokyo のため、日本時間の0:00で日付が切り替わる
        date=timezone.localdate(),
        agent_key=agent_key,
        purpose=purpose,
        model=result.model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_creation_tokens=usage.cache_creation_tokens,
        cache_read_tokens=usage.cache_read_tokens,
    )


def used_today(user):
    total = UsageRecord.objects.filter(user=user, date=timezone.localdate()).aggregate(
        total=Sum(
            F("input_tokens") + F("output_tokens")
            + F("cache_creation_tokens") + F("cache_read_tokens")
        )
    )["total"]
    return total or 0


def is_unlimited(user):
    return bool(getattr(user, "is_admin_role", False))


def remaining_percent(used, limit):
    """残りの割合（切り捨て）。わずかでも残っていれば0%にはしない。"""
    remaining = max(limit - used, 0)
    if limit <= 0 or remaining == 0:
        return 0
    return max(remaining * 100 // limit, 1)


def usage_summary(user):
    used = used_today(user)
    if is_unlimited(user):
        # 上限がないため、割合は出さない（画面では「制限なし」と表示する）
        return {
            "used": used, "limit": None, "limit_reached": False,
            "remaining_percent": None, "unlimited": True,
        }
    limit = settings.DAILY_TOKEN_LIMIT
    return {
        "used": used, "limit": limit, "limit_reached": used >= limit,
        "remaining_percent": remaining_percent(used, limit), "unlimited": False,
    }


def ensure_within_limit(user):
    """上限に達していれば 429 を返す。判定は処理の入口でのみ行う。"""
    if is_unlimited(user):
        return
    if used_today(user) >= settings.DAILY_TOKEN_LIMIT:
        raise ApiError(
            "daily_limit_reached",
            "今日はたくさんお話ししたので、ここまでにさせてください。明日になるとまた使えます。",
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
