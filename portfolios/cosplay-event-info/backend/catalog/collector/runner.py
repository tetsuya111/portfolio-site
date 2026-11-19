"""収集処理の流れ（取得 → 抽出 → 正規化 → 取り込み）をまとめる。管理コマンドから使う。"""

import logging
from collections.abc import Iterable
from datetime import date

import httpx

from catalog.collector.fetcher import Fetcher
from catalog.collector.importer import import_cosplayer, import_event
from catalog.collector.normalizer import NormalizedLocation, Normalizer
from catalog.collector.parsers.cosplayers import (
    WIKIPEDIA_CATEGORY_URL,
    parse_category_page,
    parse_person_page,
)
from catalog.collector.parsers.events import SiteConfig, parse_events

logger = logging.getLogger(__name__)

__all__ = [
    "WIKIPEDIA_CATEGORY_URL",
    "CachedNormalizer",
    "build_client",
    "run_cosplayer_collection",
    "run_event_collection",
]


def build_client() -> httpx.Client:
    """収集に使う HTTP クライアント。テストでは差し替える。"""
    return httpx.Client()


class CachedNormalizer:
    """同じ表記の正規化結果をバッチ実行中だけ覚えておき、AI の呼び出しを減らす。"""

    def __init__(self, inner: Normalizer) -> None:
        self.inner = inner
        self._cache: dict[str, NormalizedLocation] = {}

    def normalize(self, raw: str) -> NormalizedLocation:
        if raw not in self._cache:
            self._cache[raw] = self.inner.normalize(raw)
        return self._cache[raw]


def _new_counts() -> dict[str, int]:
    return {"pages": 0, "created": 0, "merged": 0, "skipped": 0, "failed": 0}


def _count_not_fetched(fetcher: Fetcher, counts: dict[str, int]) -> None:
    """fetch が None を返した理由を数える（取得済みは skipped、それ以外は failed）。"""
    counts["skipped" if fetcher.last_outcome == "skipped" else "failed"] += 1


def run_event_collection(
    fetcher: Fetcher,
    sites: Iterable[SiteConfig],
    normalizer: Normalizer,
    today: date,
    force: bool,
) -> dict[str, dict[str, int]]:
    """サイトごとにイベントを収集し、件数をサイト名ごとに返す。"""
    results: dict[str, dict[str, int]] = {}
    for site in sites:
        counts = results.setdefault(site.name, _new_counts())
        for url in site.start_urls:
            page = fetcher.fetch(url, "event", force=force)
            if page is None:
                _count_not_fetched(fetcher, counts)
                continue
            counts["pages"] += 1
            for item in parse_events(page.content, page.url, site, today):
                _, created = import_event(item, page, normalizer)
                counts["created" if created else "merged"] += 1
        logger.info("イベント収集 %s: %s", site.name, counts)
    return results


def run_cosplayer_collection(
    fetcher: Fetcher, start_url: str, limit: int | None, force: bool
) -> dict[str, int]:
    """カテゴリーページを「次のページ」までたどり、人物ページからコスプレイヤーを収集する。

    カテゴリーページ（一覧）は内容が変わるため毎回取得し、人物ページは取得済みならスキップする。
    limit は取り込む（新規・統合）人数の上限。
    """
    counts = _new_counts()
    visited: set[str] = set()
    url: str | None = start_url
    while url and url not in visited:
        visited.add(url)
        category = fetcher.fetch(url, "cosplayer", force=True)
        if category is None:
            counts["failed"] += 1
            break
        counts["pages"] += 1
        person_urls, url = parse_category_page(category.content, category.url)
        for person_url in person_urls:
            if limit is not None and counts["created"] + counts["merged"] >= limit:
                logger.info("コスプレイヤー収集: 上限 %s 人に達したため終了", limit)
                return counts
            page = fetcher.fetch(person_url, "cosplayer", force=force)
            if page is None:
                _count_not_fetched(fetcher, counts)
                continue
            counts["pages"] += 1
            item = parse_person_page(page.content, page.url)
            if not item.name:
                continue
            _, created = import_cosplayer(item, page)
            counts["created" if created else "merged"] += 1
    logger.info("コスプレイヤー収集: %s", counts)
    return counts
