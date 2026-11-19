import json

import pytest

from events.crawler.parser import extract_detail_links, parse_detail, parse_list
from events.crawler.sources import (
    DEFAULT_SOURCES_PATH,
    SourceConfigError,
    load_sources,
    parse_source,
)

DETAIL_CONFIG = parse_source(
    {
        "name": "site-a",
        "list_urls": ["https://a.example.com/list/"],
        "mode": "detail",
        "detail_link_selector": "a.event",
        "fields": {
            "title": "h1",
            "actresses": {"selector": ".actress a", "multiple": True},
            "date": ".date",
            "venue": ".place",
            "summary": ".summary",
            "note": ".note",
            "link": {"selector": "a.official", "attr": "href"},
        },
    }
)

LIST_CONFIG = parse_source(
    {
        "name": "site-b",
        "list_urls": ["https://b.example.com/schedule"],
        "mode": "list",
        "item_selector": "li.item",
        "fields": {
            "title": ".t",
            "actresses": {"selector": ".n", "multiple": True},
            "date": ".d",
            "venue": ".v",
            "link": {"selector": "a", "attr": "href"},
        },
    }
)

LIST_HTML = """
<a class="event" href="/event/1">1</a>
<a class="event" href="https://a.example.com/event/2">2</a>
<a class="event" href="/event/1">dup</a>
<a class="event" href="javascript:alert(1)">bad</a>
<a class="other" href="/about">about</a>
"""

DETAIL_HTML = """
<h1>  発売記念   サイン会 </h1>
<div class="actress"><a>山田 花子</a><a>佐藤 美咲</a><a> </a></div>
<p class="date">2026年12月3日 13:00〜</p>
<p class="place">東京都千代田区 秋葉原ホール</p>
<p class="summary">概要です</p>
<a class="official" href="/shop/1">公式</a>
"""


def test_extract_detail_links_resolves_and_dedupes():
    links = extract_detail_links(LIST_HTML, "https://a.example.com/list/", "a.event")
    assert links == ["https://a.example.com/event/1", "https://a.example.com/event/2"]


def test_parse_detail():
    raw = parse_detail(DETAIL_HTML, "https://a.example.com/event/1", DETAIL_CONFIG)
    assert raw.title == "発売記念 サイン会"
    assert raw.actresses == ["山田 花子", "佐藤 美咲"]
    assert raw.date_text == "2026年12月3日 13:00〜"
    assert raw.venue_text == "東京都千代田区 秋葉原ホール"
    assert raw.summary == "概要です"
    assert raw.note == ""
    assert raw.link == "https://a.example.com/shop/1"
    assert raw.source_url == "https://a.example.com/event/1"
    assert raw.source_name == "site-a"


def test_parse_detail_without_title_returns_none():
    assert parse_detail("<p>no title</p>", "https://a.example.com/e", DETAIL_CONFIG) is None


def test_parse_detail_drops_non_http_link():
    html = '<h1>t</h1><a class="official" href="javascript:alert(1)">x</a>'
    assert parse_detail(html, "https://a.example.com/e", DETAIL_CONFIG).link == ""


def test_parse_list():
    html = """
    <ul>
      <li class="item"><span class="t">イベントA</span><span class="n">A子</span>
        <span class="d">12/3</span><span class="v">新宿</span><a href="/e/a">詳細</a></li>
      <li class="item"><span class="t">イベントB</span><span class="d">12/4</span></li>
      <li class="item"><span class="d">タイトルなし</span></li>
    </ul>
    """
    items = parse_list(html, "https://b.example.com/schedule", LIST_CONFIG)
    assert [i.title for i in items] == ["イベントA", "イベントB"]
    assert items[0].source_url == "https://b.example.com/e/a"
    assert items[0].actresses == ["A子"]
    # 詳細リンクのない項目は一覧URL＋内容のハッシュで取得元を識別する
    assert items[1].source_url.startswith("https://b.example.com/schedule#")
    again = parse_list(html, "https://b.example.com/schedule", LIST_CONFIG)
    assert again[1].source_url == items[1].source_url


@pytest.mark.parametrize(
    "broken",
    [
        {"list_urls": ["https://x"], "mode": "detail", "fields": {"title": "h1", "date": "p"}},
        {"name": "x", "list_urls": [], "mode": "list", "fields": {"title": "h1", "date": "p"}},
        {"name": "x", "list_urls": ["https://x"], "mode": "other", "fields": {}},
        {"name": "x", "list_urls": ["https://x"], "mode": "detail", "fields": {"title": "h1"}},
        {
            "name": "x",
            "list_urls": ["https://x"],
            "mode": "detail",
            "fields": {"title": "h1", "date": "p"},
        },
        {
            "name": "x",
            "list_urls": ["https://x"],
            "mode": "list",
            "fields": {"title": "h1", "date": "p"},
        },
    ],
)
def test_invalid_config_raises(broken):
    with pytest.raises(SourceConfigError):
        parse_source(broken)


def test_bundled_sources_json_is_valid():
    sources = load_sources()
    assert {s.name for s in sources} >= {"av-event", "dmm-avevent", "pls1"}
    data = json.loads(DEFAULT_SOURCES_PATH.read_text(encoding="utf-8"))
    assert len(data["sources"]) == len(sources)


def test_duplicate_source_names_raise(tmp_path):
    src = {
        "name": "x",
        "list_urls": ["https://x"],
        "mode": "list",
        "item_selector": "li",
        "fields": {"title": "h1", "date": "p"},
    }
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"sources": [src, src]}), encoding="utf-8")
    with pytest.raises(SourceConfigError):
        load_sources(path)
