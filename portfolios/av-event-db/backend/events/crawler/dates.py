"""イベントの日付文字列の解析。"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass

_DATE_RE = re.compile(
    r"(?<!\d)(?:(?P<y>\d{4})\s*[年/.\-]\s*(?P<m>\d{1,2})\s*[月/.\-]\s*(?P<d>\d{1,2})"
    r"|(?P<m2>\d{1,2})(?:月|/)(?P<d2>\d{1,2}))(?!\d)"
)
_TIME_RE = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)")
# 年のない日付が取得日よりこれ以上前なら翌年のこととみなす
_ROLLOVER_DAYS = 60


@dataclass(frozen=True)
class EventDates:
    start_date: dt.date
    end_date: dt.date
    start_time: dt.time | None


def parse_event_dates(text: str, today: dt.date) -> EventDates | None:
    """日付を読み取る。1つ目を開始日、2つ目を終了日とする。読めなければ None。"""
    text = unicodedata.normalize("NFKC", text or "")
    matches = list(_DATE_RE.finditer(text))[:2]
    if not matches:
        return None
    try:
        start = _to_date(matches[0], ref_year=None, today=today)
        end = start
        if len(matches) == 2:
            end = _to_date(matches[1], ref_year=start.year, today=today)
            if end < start and matches[1].group("y") is None:
                end = end.replace(year=end.year + 1)
    except ValueError:
        return None
    if end < start:
        end = start
    t = _TIME_RE.search(text)
    start_time = dt.time(int(t.group(1)), int(t.group(2))) if t else None
    return EventDates(start, end, start_time)


def _to_date(m: re.Match[str], ref_year: int | None, today: dt.date) -> dt.date:
    if m.group("y"):
        return dt.date(int(m.group("y")), int(m.group("m")), int(m.group("d")))
    month, day = int(m.group("m2")), int(m.group("d2"))
    if ref_year is not None:
        return dt.date(ref_year, month, day)
    candidate = dt.date(today.year, month, day)
    if candidate < today - dt.timedelta(days=_ROLLOVER_DAYS):
        candidate = candidate.replace(year=today.year + 1)
    return candidate
