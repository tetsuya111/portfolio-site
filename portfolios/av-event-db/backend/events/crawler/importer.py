"""取り込んだイベントを DB に保存する（新規作成または既存イベントへの統合、REQ-1・REQ-3）。"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import Literal, Protocol

from django.db import transaction
from django.utils import timezone

from events.models import Actress, Event, EventSource, Venue

from .dates import EventDates, parse_event_dates
from .dedupe import find_duplicate
from .fetcher import FetchResult, FetchStatus, origin_of
from .parser import MAX_URL_LENGTH, RawEvent, extract_detail_links, parse_detail, parse_list
from .sources import SourceConfig
from .venues import VenueResolver

logger = logging.getLogger(__name__)
ImportResult = Literal["created", "merged", "skipped"]


class Fetcher(Protocol):
    def fetch(
        self, url: str, source_name: str, kind: str, cookies: dict[str, str] | None = None
    ) -> FetchResult: ...

    def mark_failed(self, url: str, error: str) -> None: ...

    def mark_unparsed(self, url: str, error: str) -> None: ...


@dataclass
class ImportStats:
    created: int = 0
    merged: int = 0
    skipped: int = 0
    failed: int = 0

    def add(self, result: ImportResult) -> None:
        setattr(self, result, getattr(self, result) + 1)


class EventImporter:
    def __init__(self, resolver: VenueResolver, today: dt.date | None = None) -> None:
        self._resolver = resolver
        self._today = today or timezone.localdate()

    def import_event(self, raw: RawEvent) -> ImportResult:
        dates = parse_event_dates(raw.date_text, today=self._today)
        if dates is None or not raw.source_url or len(raw.source_url) > MAX_URL_LENGTH:
            return "skipped"
        existing = find_duplicate(
            raw.title,
            dates.start_date,
            raw.source_url,
            dates.start_time,
            venue_id=self._resolver.known_venue_id(raw.venue_text),
        )
        # AI・ジオコーディングの通信はトランザクションの外で行い、DB のロックを長く持たない
        venue = None
        if raw.venue_text and (existing is None or existing.venue_id is None):
            venue = self._resolver.resolve(raw.venue_text)
        with transaction.atomic():
            if existing is None:
                event = self._create(raw, dates, venue)
                result: ImportResult = "created"
            else:
                event = existing
                self._merge(event, raw, dates, venue)
                result = "merged"
            EventSource.objects.get_or_create(
                source_url=raw.source_url,
                defaults={"event": event, "source_name": raw.source_name},
            )
            self._add_actresses(event, raw.actresses)
        return result

    def _create(self, raw: RawEvent, dates: EventDates, venue: Venue | None) -> Event:
        return Event.objects.create(
            title=raw.title[:300],
            start_date=dates.start_date,
            end_date=dates.end_date,
            start_time=dates.start_time,
            url=raw.link[:MAX_URL_LENGTH],
            venue=venue,
            raw_venue=raw.venue_text[:300],
            summary=raw.summary,
            note=raw.note,
        )

    def _merge(self, event: Event, raw: RawEvent, dates: EventDates, venue: Venue | None) -> None:
        """空の項目だけを新しい情報で補う（先に取り込んだ値を優先する）。"""
        if not event.url and raw.link:
            event.url = raw.link[:MAX_URL_LENGTH]
        if not event.summary and raw.summary:
            event.summary = raw.summary
        if not event.note and raw.note:
            event.note = raw.note
        if event.start_time is None and dates.start_time is not None:
            event.start_time = dates.start_time
        if event.end_date == event.start_date and dates.end_date > event.end_date:
            event.end_date = dates.end_date
        if event.venue_id is None and venue is not None:
            event.venue = venue
            event.raw_venue = event.raw_venue or raw.venue_text[:300]
        event.save()

    @staticmethod
    def _add_actresses(event: Event, names: list[str]) -> None:
        for name in names:
            actress, _ = Actress.objects.get_or_create(name=name[:100])
            event.actresses.add(actress)


def _import_raw(importer: EventImporter, raw: RawEvent, stats: ImportStats) -> ImportResult | None:
    try:
        result = importer.import_event(raw)
    except Exception:
        logger.exception("イベントの保存に失敗しました: %s", raw.source_url)
        stats.failed += 1
        return None
    stats.add(result)
    return result


def _log_unparsed(source: SourceConfig, url: str, reason: str) -> None:
    logger.warning("[%s] %s: %s", source.name, reason, url)


def run_source(
    source: SourceConfig, fetcher: Fetcher, importer: EventImporter, limit: int | None = None
) -> ImportStats:
    """1サイト分を取り込む。ページ単位の失敗は記録して続ける（REQ-1.4）。"""
    stats = ImportStats()
    seen: set[str] = set()
    # 設定の Cookie は一覧ページと同じオリジンにだけ送る（他サイトへのリンクに漏らさない）
    list_origins = {origin_of(u) for u in source.list_urls}
    processed = 0
    for list_url in source.list_urls:
        page = fetcher.fetch(list_url, source.name, "list", source.cookies or None)
        if page.status is not FetchStatus.FETCHED:
            stats.failed += 1
            continue
        if source.mode == "detail":
            assert source.detail_link_selector is not None  # noqa: S101 - parse_source で検証済み
            links = extract_detail_links(page.body, list_url, source.detail_link_selector)
            logger.info("[%s] %s から詳細ページ %d 件", source.name, list_url, len(links))
        if source.mode == "list":
            for raw in parse_list(page.body, list_url, source):
                if limit is not None and processed >= limit:
                    return stats
                processed += 1
                if _import_raw(importer, raw, stats) == "skipped":
                    _log_unparsed(
                        source, raw.source_url, f"開催日を抽出できませんでした（{raw.date_text!r}）"
                    )
            continue
        for link in links:
            if link in seen:
                continue
            seen.add(link)
            if limit is not None and processed >= limit:
                return stats
            cookies = source.cookies if origin_of(link) in list_origins else {}
            res = fetcher.fetch(link, source.name, "detail", cookies or None)
            if res.status is FetchStatus.SKIPPED:
                # 取得済みのページは通信しないため --limit の件数に数えない
                stats.skipped += 1
                continue
            processed += 1
            if res.status is not FetchStatus.FETCHED:
                stats.failed += 1
                continue
            raw = parse_detail(res.body, link, source)
            if raw is None:
                reason = (
                    f"イベント名を抽出できませんでした（title: {source.fields['title'].selector}）"
                )
                _log_unparsed(source, link, reason)
                fetcher.mark_unparsed(link, reason)
                stats.failed += 1
                continue
            result = _import_raw(importer, raw, stats)
            if result == "skipped":
                # 日付が読めないページは解析できずとして記録する（--retry-unparsed で取り直せる）
                reason = (
                    f"開催日を抽出できませんでした（date: {source.fields['date'].selector}"
                    f" → {raw.date_text!r}）"
                )
                _log_unparsed(source, link, reason)
                fetcher.mark_unparsed(link, reason)
                stats.skipped -= 1
                stats.failed += 1
            elif result is None:
                fetcher.mark_failed(link, "保存に失敗しました")
    return stats
