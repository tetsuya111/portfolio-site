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
                end = _first_valid(start.year + 1, end.month, end.day)
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
        # 終了日は開始日の年を基準にし、存在しない日付（2/29 など）は翌年以降で探す
        return _first_valid(ref_year, month, day)
    candidate = _first_valid(today.year, month, day)
    if candidate < today - dt.timedelta(days=_ROLLOVER_DAYS):
        candidate = _first_valid(today.year + 1, month, day)
    return candidate


def _first_valid(year: int, month: int, day: int) -> dt.date:
    """year 以降で month/day が存在する最初の日付。うるう日以外で存在しなければ ValueError。"""
    for y in range(year, year + 4):
        try:
            return dt.date(y, month, day)
        except ValueError:
            if (month, day) != (2, 29):
                raise
    raise ValueError(f"{month}/{day}")
