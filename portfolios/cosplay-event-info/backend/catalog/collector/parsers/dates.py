"""イベントの日付表記から開始日・終了日を読み取る。"""

import re
import unicodedata
from datetime import date, timedelta

_DATE = re.compile(
    r"(?<!\d)(?:"
    r"(?P<y>\d{4})\s*[年/.\-]\s*(?P<m>\d{1,2})\s*[月/.\-]\s*(?P<d>\d{1,2})(?!\d)日?"
    r"|(?P<m2>\d{1,2})\s*[月/]\s*(?P<d2>\d{1,2})(?!\d)日?"
    r")"
)
# 「2026.12.05 - 06」「12月5日(土)〜6日(日)」のように、範囲の後ろが日だけのもの
_BARE_DAY = re.compile(
    r"^\s*(?:[(（][^)）]{1,6}[)）])?\s*(?:[~〜\-–—]|から)\s*(?P<d>\d{1,2})日?(?![\d月/.])"
)
# 一覧ページに残っている直近の過去のイベントを翌年の予定と誤解しないための猶予
PAST_GRACE = timedelta(days=30)
_RANGE_SEPARATOR = re.compile(r"[~〜\-–—]|から")


def _build(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_match(match: re.Match[str], default_year: int) -> date | None:
    if match.group("y"):
        return _build(int(match.group("y")), int(match.group("m")), int(match.group("d")))
    return _build(default_year, int(match.group("m2")), int(match.group("d2")))


def _with_inferred_year(
    match: re.Match[str], not_before: date, grace: timedelta = timedelta(0)
) -> date | None:
    """年のない日付は (not_before − grace) 以降で最も近い年にする。"""
    value = _parse_match(match, not_before.year)
    if value and not match.group("y") and value < not_before - grace:
        value = _parse_match(match, not_before.year + 1)
    return value


def parse_date_range(text: str, today: date) -> tuple[date, date] | None:
    """開始日と終了日を返す。

    年がない日付は今年とみなし、30日より前になる場合は翌年とみなす（12月に書かれた「1/10」など）。

    終了日がない・読み取れない場合は開始日と同じ日にする。日付がなければ None。
    """
    text = unicodedata.normalize("NFKC", text or "")
    matches = [m for m in _DATE.finditer(text) if _parse_match(m, today.year)]
    if not matches:
        return None

    first = matches[0]
    start = _with_inferred_year(first, today, PAST_GRACE)
    if start is None:  # 2月29日など、補った年に存在しない日付
        return None

    end = start
    bare = _BARE_DAY.match(text[first.end() :])
    if bare:
        day = int(bare.group("d"))
        year, month = start.year, start.month
        if day < start.day:  # 「1/31〜2日」のように月をまたぐ
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        end = _build(year, month, day) or start
    elif len(matches) > 1:
        second = matches[1]
        if _RANGE_SEPARATOR.search(text[first.end() : second.start()]):
            end = _with_inferred_year(second, start) or start

    return start, max(start, end)
