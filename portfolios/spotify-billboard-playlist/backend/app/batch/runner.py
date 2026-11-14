"""DBに登録されたチャートURLを取得・解析して曲一覧を保存するバッチ処理。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from app.batch.fetcher import FetchError
from app.batch.parser import (
    ChartEntry,
    ParseError,
    find_latest_hot100_url,
    parse_chart_page,
    parse_hot100,
    parse_page_title,
)
from app.batch.urls import InvalidChartUrl, resolve_chart_url
from app.db import Database

logger = logging.getLogger(__name__)

BatchError = (InvalidChartUrl, FetchError, ParseError)


class PageFetcher(Protocol):
    def get(self, url: str) -> str: ...


@dataclass(frozen=True)
class ChartPage:
    title: str  # 解析したページの <title>（サイト名を除く。無ければ空文字）
    entries: list[ChartEntry]


def process_source(db: Database, source_id: int, fetcher: PageFetcher) -> list[ChartEntry]:
    """1件のURLを処理して曲一覧を返す。失敗時は failed を記録してから例外を送出する。"""
    return process_chart_page(db, source_id, fetcher).entries


def process_chart_page(db: Database, source_id: int, fetcher: PageFetcher) -> ChartPage:
    """1件のURLを処理し、ページのタイトルと曲一覧を返す。

    失敗時は failed を記録してから例外を送出する。
    """
    source = db.get_source(source_id)
    if source is None:
        raise KeyError(source_id)
    try:
        target = resolve_chart_url(source["url"])
        url = target.url
        if target.kind == "top":
            url = find_latest_hot100_url(fetcher.get(target.url))
        parse = parse_chart_page if target.kind == "page" else parse_hot100
        html = fetcher.get(url)
        entries = parse(html)
    except BatchError as exc:
        logger.warning("chart source %s failed: %s", source_id, exc)
        db.mark_failed(source_id, str(exc))
        raise
    except Exception:
        # 想定外の例外でも pending のまま残さない（残ると保持件数の削除対象にならず溜まり続ける）
        logger.exception("chart source %s failed unexpectedly", source_id)
        db.mark_failed(source_id, "内部エラー")
        raise
    db.mark_done(source_id, entries)
    logger.info("chart source %s done: %d tracks from %s", source_id, len(entries), url)
    return ChartPage(title=parse_page_title(html), entries=entries)


def process_pending(db: Database, fetcher: PageFetcher) -> dict[int, str]:
    """未処理のURLをすべて処理し、id ごとの結果状態を返す。"""
    results: dict[int, str] = {}
    for source_id in db.pending_ids():
        try:
            process_source(db, source_id, fetcher)
            results[source_id] = "done"
        except BatchError:
            results[source_id] = "failed"
    return results
