"""抽出ルールに従って HTML からイベント情報（RawEvent）を取り出す。"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from .sources import FieldRule, SourceConfig

_SPACES = re.compile(r"\s+")


@dataclass
class RawEvent:
    source_name: str
    source_url: str
    title: str
    date_text: str
    actresses: list[str] = field(default_factory=list)
    venue_text: str = ""
    summary: str = ""
    note: str = ""
    link: str = ""


def safe_url(href: str | None, base: str) -> str:
    """相対URLを絶対URLにし、http(s) 以外は空文字にする（NFR-3）。"""
    if not href:
        return ""
    absolute = urljoin(base, href.strip())
    parts = urlsplit(absolute)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    return absolute


def _text(el: Tag) -> str:
    return _SPACES.sub(" ", el.get_text(" ", strip=True)).strip()


def _values(root: Tag, rule: FieldRule, base: str) -> list[str]:
    elements = root.select(rule.selector) if rule.multiple else root.select(rule.selector)[:1]
    values = []
    for el in elements:
        if rule.attr:
            raw = el.get(rule.attr)
            value = raw if isinstance(raw, str) else ""
            value = safe_url(value, base) if rule.attr in ("href", "src") else value.strip()
        else:
            value = _text(el)
        if value and value not in values:
            values.append(value)
    return values


def _first(root: Tag, config: SourceConfig, name: str, base: str) -> str:
    rule = config.fields.get(name)
    if rule is None:
        return ""
    values = _values(root, rule, base)
    return values[0] if values else ""


def _build(root: Tag, config: SourceConfig, page_url: str, source_url: str) -> RawEvent | None:
    title = _first(root, config, "title", page_url)
    if not title:
        return None
    actress_rule = config.fields.get("actresses")
    return RawEvent(
        source_name=config.name,
        source_url=source_url,
        title=title,
        date_text=_first(root, config, "date", page_url),
        actresses=_values(root, actress_rule, page_url) if actress_rule else [],
        venue_text=_first(root, config, "venue", page_url),
        summary=_first(root, config, "summary", page_url),
        note=_first(root, config, "note", page_url),
        link=safe_url(_first(root, config, "link", page_url), page_url),
    )


def extract_detail_links(html: str, page_url: str, selector: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for a in soup.select(selector):
        href = a.get("href")
        url = safe_url(href if isinstance(href, str) else None, page_url)
        if url and url not in links:
            links.append(url)
    return links


def parse_detail(html: str, page_url: str, config: SourceConfig) -> RawEvent | None:
    soup = BeautifulSoup(html, "html.parser")
    return _build(soup, config, page_url, page_url)


def parse_list(html: str, page_url: str, config: SourceConfig) -> list[RawEvent]:
    """一覧ページの各項目から直接イベントを作る（詳細ページのないサイト向け）。"""
    soup = BeautifulSoup(html, "html.parser")
    events = []
    for item in soup.select(config.item_selector or ""):
        raw = _build(item, config, page_url, page_url)
        if raw is None:
            continue
        if raw.link:
            raw.source_url = raw.link
        else:
            digest = hashlib.sha256(f"{raw.title}|{raw.date_text}".encode()).hexdigest()[:16]
            raw.source_url = f"{page_url}#{digest}"
        events.append(raw)
    return events
