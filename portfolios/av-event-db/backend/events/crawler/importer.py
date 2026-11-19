"""取り込んだイベントを DB に保存する（新規作成または既存イベントへの統合、REQ-1・REQ-3）。"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import Literal, Protocol

from django.db import transaction
from django.utils import timezone

from events.models import Actress, Event, EventSource

from .dates import EventDates, parse_event_dates
from .dedupe import find_duplicate
from .fetcher import FetchResult, FetchStatus
from .parser import RawEvent, extract_detail_links, parse_detail, parse_list
from .sources import SourceConfig
from .venues import VenueResolver

logger = logging.getLogger(__name__)
ImportResult = Literal["created", "merged", "skipped"]


class Fetcher(Protocol):
    def fetch(
        self, url: str, source_name: str, kind: str, cookies: dict[str, str] | None = None
    ) -> FetchResult: ...

    def mark_failed(self, url: str, error: str) -> None: ...


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
        if dates is None:
            return "skipped"
        existing = find_duplicate(raw.title, dates.start_date, raw.source_url)
        with transaction.atomic():
            if existing is None:
                event = self._create(raw, dates)
                result: ImportResult = "created"
            else:
                event = existing
                self._merge(event, raw, dates)
                result = "merged"
            EventSource.objects.get_or_create(
                source_url=raw.source_url[:500],
                defaults={"event": event, "source_name": raw.source_name},
            )
            self._add_actresses(event, raw.actresses)
        return result

    def _create(self, raw: RawEvent, dates: EventDates) -> Event:
        return Event.objects.create(
            title=raw.title[:300],
            start_date=dates.start_date,
            end_date=dates.end_date,
            start_time=dates.start_time,
            url=raw.link[:500],
            venue=self._resolver.resolve(raw.venue_text),
            raw_venue=raw.venue_text[:300],
            summary=raw.summary,
            note=raw.note,
        )

    def _merge(self, event: Event, raw: RawEvent, dates: EventDates) -> None:
        """空の項目だけを新しい情報で補う（先に取り込んだ値を優先する）。"""
        if not event.url and raw.link:
            event.url = raw.link[:500]
        if not event.summary and raw.summary:
            event.summary = raw.summary
        if not event.note and raw.note:
            event.note = raw.note
        if event.start_time is None and dates.start_time is not None:
            event.start_time = dates.start_time
        if event.end_date == event.start_date and dates.end_date > event.end_date:
            event.end_date = dates.end_date
        if event.venue_id is None and raw.venue_text:
            event.venue = self._resolver.resolve(raw.venue_text)
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


def run_source(
    source: SourceConfig, fetcher: Fetcher, importer: EventImporter, limit: int | None = None
) -> ImportStats:
    """1サイト分を取り込む。ページ単位の失敗は記録して続ける（REQ-1.4）。"""
    stats = ImportStats()
    seen: set[str] = set()
    processed = 0
    for list_url in source.list_urls:
        page = fetcher.fetch(list_url, source.name, "list", source.cookies or None)
        if page.status is not FetchStatus.FETCHED:
            stats.failed += 1
            continue
        if source.mode == "list":
            for raw in parse_list(page.body, list_url, source):
                if limit is not None and processed >= limit:
                    return stats
                processed += 1
                _import_raw(importer, raw, stats)
            continue
        assert source.detail_link_selector is not None  # noqa: S101 - parse_source で検証済み
        for link in extract_detail_links(page.body, list_url, source.detail_link_selector):
            if link in seen:
                continue
            seen.add(link)
            if limit is not None and processed >= limit:
                return stats
            processed += 1
            res = fetcher.fetch(link, source.name, "detail", source.cookies or None)
            if res.status is FetchStatus.SKIPPED:
                stats.skipped += 1
                continue
            if res.status is not FetchStatus.FETCHED:
                stats.failed += 1
                continue
            raw = parse_detail(res.body, link, source)
            if raw is None:
                fetcher.mark_failed(link, "イベント名を抽出できませんでした")
                stats.failed += 1
                continue
            result = _import_raw(importer, raw, stats)
            if result == "skipped":
                # 日付が読めないページは抽出ルールの修正後に取り直せるよう失敗扱いにする
                fetcher.mark_failed(link, "開催日を抽出できませんでした")
                stats.skipped -= 1
                stats.failed += 1
            elif result is None:
                fetcher.mark_failed(link, "保存に失敗しました")
    return stats
