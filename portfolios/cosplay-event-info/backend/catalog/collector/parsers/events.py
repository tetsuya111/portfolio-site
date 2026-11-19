"""イベント一覧ページからイベントを抽出する（EV-1）。

schema.org の Event（JSON-LD）があればそれを使い、なければサイトごとの CSS セレクターで抽出する。
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from bs4 import BeautifulSoup, Tag

from catalog.collector.parsers import absolute_http_url
from catalog.collector.parsers.dates import parse_date_range

MAX_NOTES_LENGTH = 1000
# 日本時間（夏時間がないため固定オフセットで扱い、tz データベースに依存しない）
JAPAN = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class EventItem:
    name: str
    url: str
    location: str
    start_date: date
    end_date: date
    notes: str


@dataclass(frozen=True)
class SiteConfig:
    """サイトごとの抽出ルール。セレクターは BeautifulSoup の CSS セレクター。"""

    name: str
    start_urls: tuple[str, ...]
    item: str
    name_sel: str
    link: str | None = None
    date: str | None = None
    location: str | None = None
    notes: str | None = None


# 対象サイト。HTML 構造は未確認のため、ブログ形式のサイトで一般的なセレクターを既定にしている。
# 実サイトに合わせて調整する（README の「対象サイトの抽出ルール」を参照）。
_GENERIC: dict[str, str] = {
    "item": "article",
    "name_sel": ".entry-title, h2, h3",
    "link": "a[href]",
    "date": "time, .date, .event-date",
    "location": ".place, .venue, .location, .event-place",
    "notes": ".excerpt, .entry-summary, .summary",
}

SITES: dict[str, SiteConfig] = {
    "cos-cam": SiteConfig(name="cos-cam", start_urls=("https://cos-cam.work/",), **_GENERIC),
    "cos-compass": SiteConfig(
        name="cos-compass", start_urls=("https://cos-compass.com/event/",), **_GENERIC
    ),
    "cossuke": SiteConfig(name="cossuke", start_urls=("https://cossuke.jp/",), **_GENERIC),
    "cospot": SiteConfig(
        name="cospot", start_urls=("https://cospot-media.com/category/event-list/",), **_GENERIC
    ),
}


def _text(node: Tag | None) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


# ---- JSON-LD ----


def _is_event(obj: dict[str, Any]) -> bool:
    types = obj.get("@type")
    types = types if isinstance(types, list) else [types]
    return any(isinstance(t, str) and t.endswith("Event") for t in types)


def _walk(obj: Any) -> Iterator[dict[str, Any]]:
    if isinstance(obj, list):
        for x in obj:
            yield from _walk(x)
    elif isinstance(obj, dict):
        if _is_event(obj):
            yield obj
            return
        # @graph や ItemList の itemListElement[].item など、入れ子の中も探す
        for value in obj.values():
            yield from _walk(value)


def _iso_date(value: Any) -> date | None:
    """ISO 8601 の日付・日時を日本時間の日付にする（UTC の日時は日付がずれうるため変換する）。"""
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        if len(value) == 10:
            return date.fromisoformat(value)
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(JAPAN)
    return parsed.date()


def _str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _location_text(location: Any) -> str:
    if isinstance(location, str):
        return location.strip()
    if isinstance(location, list):
        return " ".join(filter(None, (_location_text(x) for x in location)))
    if not isinstance(location, dict):
        return ""
    address = location.get("address")
    if isinstance(address, dict):
        keys = ("addressRegion", "addressLocality", "streetAddress")
        address = "".join(_str(address.get(k)) for k in keys)
    return " ".join(x for x in (_str(location.get("name")), _str(address)) if x)


def parse_jsonld_events(html: str, base_url: str) -> list[EventItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[EventItem] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except ValueError:
            continue
        for obj in _walk(data):
            name = _str(obj.get("name"))
            start = _iso_date(obj.get("startDate"))
            if not name or not start:
                continue
            end = _iso_date(obj.get("endDate")) or start
            items.append(
                EventItem(
                    name=name,
                    url=absolute_http_url(_str(obj.get("url")), base_url),
                    location=_location_text(obj.get("location")),
                    start_date=start,
                    end_date=max(start, end),
                    notes=_str(obj.get("description"))[:MAX_NOTES_LENGTH],
                )
            )
    return items


# ---- CSS セレクター ----


def _select_text(node: Tag, selector: str | None) -> str:
    return _text(node.select_one(selector)) if selector else ""


def parse_with_selectors(
    html: str, base_url: str, config: SiteConfig, today: date
) -> list[EventItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[EventItem] = []
    for node in soup.select(config.item):
        name = _select_text(node, config.name_sel)
        # 日付のセレクターに当たる要素がなければ、項目全体の文章から探す
        date_text = _select_text(node, config.date) or _text(node)
        dates = parse_date_range(date_text, today)
        if not name or not dates:
            continue
        link = node.select_one(config.link) if config.link else None
        href = link.get("href") if link else None
        items.append(
            EventItem(
                name=name,
                url=absolute_http_url(href if isinstance(href, str) else None, base_url),
                location=_select_text(node, config.location),
                start_date=dates[0],
                end_date=dates[1],
                notes=_select_text(node, config.notes)[:MAX_NOTES_LENGTH],
            )
        )
    return items


def parse_events(html: str, base_url: str, config: SiteConfig, today: date) -> list[EventItem]:
    """JSON-LD で1件以上取れればそれを、なければセレクターで抽出した結果を返す。"""
    return parse_jsonld_events(html, base_url) or parse_with_selectors(
        html, base_url, config, today
    )
