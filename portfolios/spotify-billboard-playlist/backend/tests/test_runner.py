from pathlib import Path

import pytest

from app.batch.fetcher import FetchError
from app.batch.parser import ParseError
from app.batch.runner import process_pending, process_source
from app.batch.urls import InvalidChartUrl
from app.db import Database

FIXTURES = Path(__file__).parent / "fixtures"
HOT_URL = "https://billboard.mryogaku.com/php/dispHot100.php?date=2025-11-15"
LATEST_URL = "https://billboard.mryogaku.com/php/dispHot100.php?date=2026-11-14"


class FakeFetcher:
    def __init__(self, pages: dict[str, str] | None = None, error: Exception | None = None):
        self.pages = pages or {}
        self.error = error
        self.calls: list[str] = []

    def get(self, url: str) -> str:
        self.calls.append(url)
        if self.error:
            raise self.error
        return self.pages[url]


@pytest.fixture
def db():
    return Database(":memory:")


def _hot100() -> str:
    return (FIXTURES / "hot100.html").read_text(encoding="utf-8")


def test_process_hot100_source(db):
    sid = db.add_source("https://billboard.mryogaku.com/php/chart.php?date=2025-11-15")
    fetcher = FakeFetcher({HOT_URL: _hot100()})
    entries = process_source(db, sid, fetcher)
    assert [e.rank for e in entries] == [1, 2, 99]
    assert fetcher.calls == [HOT_URL]
    assert db.get_source(sid)["status"] == "done"
    assert db.tracks(sid) == entries


def test_process_top_source_follows_latest(db):
    sid = db.add_source("https://billboard.mryogaku.com/#google_vignette")
    top = (FIXTURES / "top.html").read_text(encoding="utf-8")
    fetcher = FakeFetcher({"https://billboard.mryogaku.com/": top, LATEST_URL: _hot100()})
    entries = process_source(db, sid, fetcher)
    assert len(entries) == 3
    assert fetcher.calls == ["https://billboard.mryogaku.com/", LATEST_URL]


def test_invalid_url_marked_failed(db):
    sid = db.add_source("https://example.com/")
    with pytest.raises(InvalidChartUrl):
        process_source(db, sid, FakeFetcher())
    source = db.get_source(sid)
    assert source["status"] == "failed"
    assert "billboard.mryogaku.com" in source["error"]


def test_fetch_error_marked_failed(db):
    sid = db.add_source(HOT_URL)
    with pytest.raises(FetchError):
        process_source(db, sid, FakeFetcher(error=FetchError("boom")))
    assert db.get_source(sid)["status"] == "failed"
    assert db.get_source(sid)["error"] == "boom"


def test_parse_error_marked_failed(db):
    sid = db.add_source(HOT_URL)
    with pytest.raises(ParseError):
        process_source(db, sid, FakeFetcher({HOT_URL: "<html></html>"}))
    assert db.get_source(sid)["status"] == "failed"


def test_process_pending_handles_all(db):
    ok = db.add_source(HOT_URL)
    bad = db.add_source("https://example.com/")
    result = process_pending(db, FakeFetcher({HOT_URL: _hot100()}))
    assert result == {ok: "done", bad: "failed"}
    assert db.pending_ids() == []


def test_reprocess_replaces_tracks(db):
    sid = db.add_source(HOT_URL)
    fetcher = FakeFetcher({HOT_URL: _hot100()})
    process_source(db, sid, fetcher)
    process_source(db, sid, fetcher)
    assert len(db.tracks(sid)) == 3


def test_get_unknown_source(db):
    assert db.get_source(999) is None
