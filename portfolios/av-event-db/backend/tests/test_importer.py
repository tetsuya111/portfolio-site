import datetime as dt
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from events.crawler.fetcher import FetchResult, FetchStatus
from events.crawler.importer import EventImporter, run_source
from events.crawler.parser import RawEvent
from events.crawler.sources import parse_source
from events.crawler.venues import NormalizedVenue, VenueResolver
from events.management.commands import fetch_events
from events.models import Event, EventSource, FetchedPage

pytestmark = pytest.mark.django_db
TODAY = dt.date(2026, 11, 19)


class FakeNormalizer:
    def __init__(self):
        self.calls = 0

    def normalize(self, text):
        self.calls += 1
        return NormalizedVenue(name=text, address="", prefecture="東京都")


def importer(normalizer=None):
    return EventImporter(VenueResolver(normalizer or FakeNormalizer(), None), today=TODAY)


def raw(**kw):
    base = {
        "source_name": "site-a",
        "source_url": "https://a.example.com/event/1",
        "title": "新作発売記念サイン会 in 秋葉原",
        "date_text": "2026/12/3 13:00",
        "actresses": ["山田花子"],
        "venue_text": "秋葉原ホール",
        "summary": "",
        "note": "",
        "link": "",
    }
    base.update(kw)
    return RawEvent(**base)


def test_creates_event():
    assert importer().import_event(raw(summary="概要")) == "created"
    e = Event.objects.get()
    assert e.title == "新作発売記念サイン会 in 秋葉原"
    assert e.start_date == dt.date(2026, 12, 3)
    assert e.start_time == dt.time(13, 0)
    assert e.venue.name == "秋葉原ホール"
    assert e.raw_venue == "秋葉原ホール"
    assert [a.name for a in e.actresses.all()] == ["山田花子"]
    assert list(e.sources.values_list("source_url", flat=True)) == ["https://a.example.com/event/1"]


def test_merges_similar_event_from_other_site():
    imp = importer()
    imp.import_event(raw(summary="", link=""))
    result = imp.import_event(
        raw(
            source_name="site-b",
            source_url="https://b.example.com/x/9",
            title="【新作発売記念】サイン会in秋葉原",
            actresses=["山田花子", "佐藤美咲"],
            summary="B の概要",
            note="整理券あり",
            link="https://shop.example.com/1",
            date_text="2026年12月3日〜12月4日",
        )
    )
    assert result == "merged"
    e = Event.objects.get()
    assert e.title == "新作発売記念サイン会 in 秋葉原"  # 先に取り込んだ方を優先
    assert e.summary == "B の概要"
    assert e.note == "整理券あり"
    assert e.url == "https://shop.example.com/1"
    assert e.end_date == dt.date(2026, 12, 4)
    assert sorted(a.name for a in e.actresses.all()) == ["佐藤美咲", "山田花子"]
    assert EventSource.objects.filter(event=e).count() == 2


def test_merge_does_not_overwrite_existing_values():
    imp = importer()
    imp.import_event(raw(summary="A の概要"))
    imp.import_event(raw(source_url="https://b.example.com/1", summary="B の概要"))
    assert Event.objects.get().summary == "A の概要"


def test_merge_skips_venue_resolution_when_venue_exists():
    norm = FakeNormalizer()
    imp = importer(norm)
    imp.import_event(raw())
    imp.import_event(raw(source_url="https://b.example.com/1", venue_text="別表記の会場"))
    assert norm.calls == 1


def test_different_day_creates_new_event():
    imp = importer()
    imp.import_event(raw())
    assert imp.import_event(raw(source_url="https://a.example.com/2", date_text="2026/12/4")) == (
        "created"
    )
    assert Event.objects.count() == 2


def test_unreadable_date_is_skipped():
    assert importer().import_event(raw(date_text="近日公開")) == "skipped"
    assert Event.objects.count() == 0


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []
        self.failed = []

    def fetch(self, url, source_name, kind, cookies=None):
        self.calls.append((url, kind, cookies))
        page = self.pages.get(url)
        if page is None:
            return FetchResult(FetchStatus.FAILED)
        if page == "skip":
            return FetchResult(FetchStatus.SKIPPED)
        return FetchResult(FetchStatus.FETCHED, page)

    def mark_failed(self, url, error):
        self.failed.append(url)

    def close(self):
        pass


DETAIL_SOURCE = parse_source(
    {
        "name": "site-a",
        "list_urls": ["https://a.example.com/list/"],
        "mode": "detail",
        "detail_link_selector": "a.e",
        "cookies": {"age": "1"},
        "fields": {"title": "h1", "date": ".d", "venue": ".v"},
    }
)


def detail(title, date="2026/12/3"):
    return f'<h1>{title}</h1><p class="d">{date}</p><p class="v">会場</p>'


def test_run_source_detail_mode_continues_after_failures():
    fetcher = FakeFetcher(
        {
            "https://a.example.com/list/": (
                '<a class="e" href="/1">1</a><a class="e" href="/2">2</a>'
                '<a class="e" href="/3">3</a><a class="e" href="/4">4</a>'
                '<a class="e" href="/5">5</a>'
            ),
            "https://a.example.com/1": detail("イベント1"),
            # /2 は取得失敗
            "https://a.example.com/3": "skip",
            "https://a.example.com/4": "<p>タイトルなし</p>",
            "https://a.example.com/5": detail("イベント5", date="未定"),
        }
    )
    stats = run_source(DETAIL_SOURCE, fetcher, importer())
    assert (stats.created, stats.merged, stats.skipped, stats.failed) == (1, 0, 1, 3)
    assert fetcher.calls[0] == ("https://a.example.com/list/", "list", {"age": "1"})
    assert fetcher.failed == ["https://a.example.com/4", "https://a.example.com/5"]


def test_run_source_respects_limit():
    fetcher = FakeFetcher(
        {
            "https://a.example.com/list/": '<a class="e" href="/1">1</a><a class="e" href="/2">2</a>',
            "https://a.example.com/1": detail("イベント1"),
            "https://a.example.com/2": detail("イベント2"),
        }
    )
    stats = run_source(DETAIL_SOURCE, fetcher, importer(), limit=1)
    assert stats.created == 1
    assert len(fetcher.calls) == 2


def test_run_source_list_mode():
    source = parse_source(
        {
            "name": "site-b",
            "list_urls": ["https://b.example.com/s"],
            "mode": "list",
            "item_selector": "li",
            "fields": {"title": ".t", "date": ".d"},
        }
    )
    html = (
        '<li><span class="t">A</span><span class="d">12/3</span></li>'
        '<li><span class="t">B</span><span class="d">12/4</span></li>'
    )
    stats = run_source(source, FakeFetcher({"https://b.example.com/s": html}), importer())
    assert stats.created == 2


def test_run_source_list_page_failure():
    stats = run_source(DETAIL_SOURCE, FakeFetcher({}), importer())
    assert stats.failed == 1


SOURCES_JSON = """
{"sources": [
  {"name": "site-a", "list_urls": ["https://a.example.com/list/"], "mode": "detail",
   "detail_link_selector": "a.e", "fields": {"title": "h1", "date": ".d"}},
  {"name": "site-b", "list_urls": ["https://b.example.com/s"], "mode": "list",
   "item_selector": "li", "fields": {"title": ".t", "date": ".d"}}
]}
"""


@pytest.fixture
def command_env(tmp_path, monkeypatch, settings):
    settings.ANTHROPIC_API_KEY = ""
    settings.GOOGLE_MAPS_GEOCODING_API_KEY = ""
    path = tmp_path / "sources.json"
    path.write_text(SOURCES_JSON, encoding="utf-8")
    fetcher = FakeFetcher(
        {
            "https://a.example.com/list/": '<a class="e" href="/1">1</a>',
            "https://a.example.com/1": detail("イベント1"),
            "https://b.example.com/s": '<li><span class="t">B</span><span class="d">12/4</span></li>',
        }
    )
    monkeypatch.setattr(fetch_events, "build_fetcher", lambda: fetcher)
    return path, fetcher


def test_command_runs_all_sources(command_env):
    path, _ = command_env
    out = StringIO()
    call_command("fetch_events", "--sources-file", str(path), stdout=out)
    assert Event.objects.count() == 2
    assert "site-a: 作成 1 / 統合 0 / スキップ 0 / 失敗 0" in out.getvalue()
    assert "site-b: 作成 1" in out.getvalue()


def test_command_filters_sources(command_env):
    path, fetcher = command_env
    call_command(
        "fetch_events", "--sources-file", str(path), "--source", "site-b", stdout=StringIO()
    )
    assert [c[0] for c in fetcher.calls] == ["https://b.example.com/s"]


def test_command_unknown_source(command_env):
    path, _ = command_env
    with pytest.raises(CommandError):
        call_command("fetch_events", "--sources-file", str(path), "--source", "nope")


def test_seed_demo_is_idempotent():
    call_command("seed_demo", stdout=StringIO())
    count = Event.objects.count()
    assert count >= 10
    call_command("seed_demo", stdout=StringIO())
    assert Event.objects.count() == count
    assert Event.objects.filter(venue__latitude__isnull=False).exists()
    assert not FetchedPage.objects.exists()
