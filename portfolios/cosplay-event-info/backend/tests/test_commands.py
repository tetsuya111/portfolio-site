from datetime import date
from pathlib import Path

import httpx
import pytest
from django.core.management import CommandError, call_command

from catalog.collector import runner
from catalog.collector.fetcher import Fetcher
from catalog.collector.normalizer import RuleBasedNormalizer
from catalog.collector.parsers import events as events_module
from catalog.collector.parsers.events import SiteConfig
from catalog.models import Cosplayer, Event, FetchedPage

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 11, 19)


def site(name, url):
    return SiteConfig(
        name=name,
        start_urls=(url,),
        item="article.event",
        name_sel="h2",
        link="h2 a",
        date=".date",
        location=".place",
        notes=".excerpt",
    )


class Web:
    """URL ごとの応答を返す偽の Web。呼ばれた URL を記録する。"""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def handler(self, request):
        url = str(request.url)
        self.calls.append(url)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if url not in self.pages:
            return httpx.Response(500)
        return httpx.Response(200, text=self.pages[url])

    def client(self):
        return httpx.Client(transport=httpx.MockTransport(self.handler))

    def fetcher(self):
        return Fetcher(self.client(), min_interval=0, sleep=lambda s: None)


LIST_HTML = (FIXTURES / "events_list.html").read_text(encoding="utf-8")


def test_event_collection_imports_and_second_run_skips():
    web = Web({"https://a.example/events": LIST_HTML})
    sites = [site("a", "https://a.example/events")]

    first = runner.run_event_collection(
        web.fetcher(), sites, RuleBasedNormalizer(), TODAY, force=False
    )
    second = runner.run_event_collection(
        web.fetcher(), sites, RuleBasedNormalizer(), TODAY, force=False
    )

    assert first["a"] == {"pages": 1, "created": 2, "merged": 0, "skipped": 0, "failed": 0}
    assert second["a"] == {"pages": 0, "created": 0, "merged": 0, "skipped": 1, "failed": 0}
    assert Event.objects.count() == 2


def test_event_collection_force_refetches_and_merges():
    web = Web({"https://a.example/events": LIST_HTML})
    sites = [site("a", "https://a.example/events")]
    runner.run_event_collection(web.fetcher(), sites, RuleBasedNormalizer(), TODAY, force=False)

    result = runner.run_event_collection(
        web.fetcher(), sites, RuleBasedNormalizer(), TODAY, force=True
    )

    assert result["a"]["merged"] == 2
    assert Event.objects.count() == 2


def test_failed_site_does_not_stop_others():
    web = Web({"https://b.example/events": LIST_HTML})
    sites = [site("a", "https://a.example/events"), site("b", "https://b.example/events")]

    result = runner.run_event_collection(
        web.fetcher(), sites, RuleBasedNormalizer(), TODAY, force=False
    )

    assert result["a"]["failed"] == 1
    assert result["b"]["created"] == 2


@pytest.fixture
def fake_web(monkeypatch, settings):
    settings.FETCH_MIN_INTERVAL = 0
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def install(pages):
        web = Web(pages)
        monkeypatch.setattr(runner, "build_client", web.client)
        return web

    return install


def test_fetch_events_command_with_site_option(fake_web, monkeypatch):
    web = fake_web({"https://a.example/events": LIST_HTML, "https://b.example/events": LIST_HTML})
    monkeypatch.setattr(
        events_module,
        "SITES",
        {"a": site("a", "https://a.example/events"), "b": site("b", "https://b.example/events")},
    )

    call_command("fetch_events", "--site", "b")

    assert "https://b.example/events" in web.calls
    assert "https://a.example/events" not in web.calls
    assert Event.objects.count() == 2


def test_fetch_events_command_fails_when_all_sites_fail(fake_web, monkeypatch):
    fake_web({})
    monkeypatch.setattr(events_module, "SITES", {"a": site("a", "https://a.example/events")})

    with pytest.raises(CommandError):
        call_command("fetch_events")


CATEGORY = "https://wiki.example/wiki/Category:X"


def category_html(people, next_href=None):
    items = "".join(f'<li><a href="/wiki/{p}">{p}</a></li>' for p in people)
    next_link = f'<a href="{next_href}">次のページ</a>' if next_href else ""
    return f'<div id="mw-pages">{next_link}<ul>{items}</ul></div>'


def person_html(name):
    return (
        f'<h1 id="firstHeading">{name}</h1><div class="mw-parser-output"><p>{name}の説明。</p>'
        '<a href="https://x.com/' + name + '">X</a></div>'
    )


def test_cosplayer_collection_follows_next_page_and_skips_fetched():
    web = Web(
        {
            CATEGORY: category_html(["alice"], next_href="/wiki/Category:X?page=2"),
            "https://wiki.example/wiki/Category:X?page=2": category_html(["bob"]),
            "https://wiki.example/wiki/alice": person_html("alice"),
            "https://wiki.example/wiki/bob": person_html("bob"),
        }
    )

    first = runner.run_cosplayer_collection(web.fetcher(), CATEGORY, limit=None, force=False)
    second = runner.run_cosplayer_collection(web.fetcher(), CATEGORY, limit=None, force=False)

    assert first["created"] == 2
    assert second["skipped"] == 2
    assert second["created"] == 0
    assert Cosplayer.objects.count() == 2
    # 一覧（カテゴリーページ）は毎回取得し直す
    assert web.calls.count(CATEGORY) == 2


def test_fetch_cosplayers_stops_on_visited_page():
    web = Web({CATEGORY: category_html(["alice"], next_href="/wiki/Category:X")})
    web.pages["https://wiki.example/wiki/alice"] = person_html("alice")

    result = runner.run_cosplayer_collection(web.fetcher(), CATEGORY, limit=None, force=False)

    assert result["created"] == 1
    assert web.calls.count(CATEGORY) == 1


def test_cosplayer_collection_limit():
    web = Web(
        {
            CATEGORY: category_html(["alice", "bob"]),
            "https://wiki.example/wiki/alice": person_html("alice"),
            "https://wiki.example/wiki/bob": person_html("bob"),
        }
    )

    result = runner.run_cosplayer_collection(web.fetcher(), CATEGORY, limit=1, force=False)

    assert result["created"] == 1
    assert "https://wiki.example/wiki/bob" not in web.calls


def test_fetch_cosplayers_command(fake_web, monkeypatch):
    fake_web(
        {
            CATEGORY: category_html(["alice"]),
            "https://wiki.example/wiki/alice": person_html("alice"),
        }
    )
    monkeypatch.setattr(runner, "WIKIPEDIA_CATEGORY_URL", CATEGORY)

    call_command("fetch_cosplayers", "--limit", "5")

    assert Cosplayer.objects.get().sns_links == ["https://x.com/alice"]
    assert FetchedPage.objects.filter(kind="cosplayer").count() == 2


def test_seed_demo_is_idempotent():
    call_command("seed_demo")
    counts = (Event.objects.count(), Cosplayer.objects.count())

    call_command("seed_demo")

    assert counts[0] >= 10
    assert counts[1] >= 5
    assert (Event.objects.count(), Cosplayer.objects.count()) == counts
    assert Event.objects.filter(venue__isnull=False).count() == counts[0]
