"""チャートURLの検証と正規化。取得先は billboard.mryogaku.com に限定する。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal
from urllib.parse import parse_qs, urlsplit

HOST = "billboard.mryogaku.com"
TOP_URL = f"https://{HOST}/"
HOT100_URL = f"https://{HOST}/php/dispHot100.php?date={{date}}"
MAX_URL_LENGTH = 2048

_TOP_PATHS = {"", "/", "/index.php", "/s", "/s/", "/s/index.php"}
_CHART_PATHS = {
    "/php/chart.php",
    "/php/dispHot100.php",
    "/s/php/chart.php",
    "/s/php/dispHot100.php",
}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class InvalidChartUrl(ValueError):
    """受け付けられないチャートURL。"""


@dataclass(frozen=True)
class ChartTarget:
    kind: Literal["top", "hot100"]
    url: str


def resolve_chart_url(url: str) -> ChartTarget:
    """入力URLを検証し、取得すべき正規化済みURLを返す。"""
    url = url.strip()
    if not url or len(url) > MAX_URL_LENGTH:
        raise InvalidChartUrl("URLが空か長すぎます")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise InvalidChartUrl("URLの形式が正しくありません") from exc
    if parts.scheme not in ("https", "http"):
        raise InvalidChartUrl("http(s) のURLを指定してください")
    if (parts.hostname or "").lower() != HOST or port is not None:
        raise InvalidChartUrl(f"{HOST} のURLのみ指定できます")
    if parts.username is not None or parts.password is not None:
        raise InvalidChartUrl("ユーザー情報付きのURLは指定できません")

    if parts.path in _TOP_PATHS:
        return ChartTarget("top", TOP_URL)
    if parts.path in _CHART_PATHS:
        dates = parse_qs(parts.query).get("date", [])
        if len(dates) != 1 or not _is_valid_date(dates[0]):
            raise InvalidChartUrl("date=YYYY-MM-DD の指定が必要です")
        return ChartTarget("hot100", HOT100_URL.format(date=dates[0]))
    raise InvalidChartUrl(
        "チャートページ（トップ / chart.php / dispHot100.php）のURLを指定してください"
    )


def _is_valid_date(value: str) -> bool:
    if not _DATE_RE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
