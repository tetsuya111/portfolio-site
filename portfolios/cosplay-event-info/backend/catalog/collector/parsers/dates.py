"""イベントの日付表記から開始日・終了日を読み取る。"""

import re
import unicodedata
from datetime import date

_DATE = re.compile(
    r"(?<!\d)(?:"
    r"(?P<y>\d{4})\s*[年/.\-]\s*(?P<m>\d{1,2})\s*[月/.\-]\s*(?P<d>\d{1,2})(?!\d)日?"
    r"|(?P<m2>\d{1,2})\s*[月/]\s*(?P<d2>\d{1,2})(?!\d)日?"
    r")"
)
# 「2026.12.05 - 06」のように、範囲の後ろが日だけのもの
_BARE_DAY = re.compile(r"^\s*(?:[~〜\-–—]|から)\s*(?P<d>\d{1,2})日?(?![\d月/.])")
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


def _with_inferred_year(match: re.Match[str], not_before: date) -> date | None:
    """年のない日付は not_before 以降で最も近い年にする。"""
    value = _parse_match(match, not_before.year)
    if value and not match.group("y") and value < not_before:
        value = _parse_match(match, not_before.year + 1)
    return value


def parse_date_range(text: str, today: date) -> tuple[date, date] | None:
    """開始日と終了日を返す。年がない日付は today 以降で最も近い年とみなす。

    終了日がない・読み取れない場合は開始日と同じ日にする。日付がなければ None。
    """
    text = unicodedata.normalize("NFKC", text or "")
    matches = [m for m in _DATE.finditer(text) if _parse_match(m, today.year)]
    if not matches:
        return None

    first = matches[0]
    start = _with_inferred_year(first, today)
    if start is None:  # 2月29日など、補った年に存在しない日付
        return None

    end = start
    bare = _BARE_DAY.match(text[first.end() :])
    if bare:
        end = _build(start.year, start.month, int(bare.group("d"))) or start
    elif len(matches) > 1:
        second = matches[1]
        if _RANGE_SEPARATOR.search(text[first.end() : second.start()]):
            end = _with_inferred_year(second, start) or start

    return start, max(start, end)
