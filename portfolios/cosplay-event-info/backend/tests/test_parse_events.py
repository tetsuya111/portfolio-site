from datetime import date
from pathlib import Path

import pytest

from catalog.collector.parsers.dates import parse_date_range
from catalog.collector.parsers.events import SITES, EventItem, SiteConfig, parse_events

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 11, 19)

CONFIG = SiteConfig(
    name="test",
    start_urls=("https://example.com/events/",),
    item="article.event",
    name_sel="h2",
    link="h2 a",
    date=".date",
    location=".place",
    notes=".excerpt",
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026年12月5日", (date(2026, 12, 5), date(2026, 12, 5))),
        ("２０２６年１２月５日（土）", (date(2026, 12, 5), date(2026, 12, 5))),
        ("2026/12/5〜2026/12/6", (date(2026, 12, 5), date(2026, 12, 6))),
        ("12/5(土)〜12/6(日)", (date(2026, 12, 5), date(2026, 12, 6))),
        ("2026.12.05 - 06", (date(2026, 12, 5), date(2026, 12, 6))),
        ("2026-12-05", (date(2026, 12, 5), date(2026, 12, 5))),
        ("12月31日〜1月2日", (date(2026, 12, 31), date(2027, 1, 2))),
    ],
)
def test_parse_date_range(text, expected):
    assert parse_date_range(text, TODAY) == expected


def test_parse_date_range_rolls_over_year():
    assert parse_date_range("1/10(土)", date(2026, 12, 20)) == (
        date(2027, 1, 10),
        date(2027, 1, 10),
    )


def test_parse_date_range_single_day():
    start, end = parse_date_range("開催日: 12月5日 開場10:00", TODAY)

    assert start == end == date(2026, 12, 5)


@pytest.mark.parametrize("text", ["", "近日公開", "13/45", "1-2F"])
def test_parse_date_range_without_date(text):
    assert parse_date_range(text, TODAY) is None


def test_jsonld_events_are_extracted():
    html = (FIXTURES / "events_jsonld.html").read_text(encoding="utf-8")

    items = parse_events(html, "https://example.com/list", CONFIG, TODAY)

    assert items == [
        EventItem(
            name="コスプレフェスタ冬",
            url="https://example.com/events/winter",
            location="東京ビッグサイト 東京都江東区有明3-11-1",
            start_date=date(2026, 12, 5),
            end_date=date(2026, 12, 6),
            notes="冬の大型コスプレイベント",
        ),
        EventItem(
            name="撮影会 in 大阪",
            url="",
            location="インテックス大阪",
            start_date=date(2027, 1, 10),
            end_date=date(2027, 1, 10),
            notes="",
        ),
    ]


def test_selector_events_are_extracted_when_no_jsonld():
    html = (FIXTURES / "events_list.html").read_text(encoding="utf-8")

    items = parse_events(html, "https://example.com/events/", CONFIG, TODAY)

    assert [i.name for i in items] == ["となりのコスプレ祭り", "ホココス"]
    first, second = items
    assert first.url == "https://example.com/event/101"
    assert (first.start_date, first.end_date) == (date(2026, 12, 5), date(2026, 12, 6))
    assert first.location == "池袋サンシャインシティ 文化会館"
    assert first.notes == "撮影エリアあり"
    assert second.url == "https://other.example.com/e/2"
    assert second.start_date == date(2027, 1, 17)


def test_unsafe_link_is_dropped():
    html = (
        '<article class="event"><h2><a href="javascript:alert(1)">X</a></h2>'
        '<span class="date">12/5</span></article>'
    )

    items = parse_events(html, "https://example.com/", CONFIG, TODAY)

    assert items[0].url == ""


def test_sites_cover_target_sites():
    urls = {u for site in SITES.values() for u in site.start_urls}

    assert urls == {
        "https://cos-cam.work/",
        "https://cos-compass.com/event/",
        "https://cossuke.jp/",
        "https://cospot-media.com/category/event-list/",
    }


def test_parse_date_range_weekday_before_bare_end_day():
    assert parse_date_range("2026年12月5日(土)〜6日(日)", TODAY) == (
        date(2026, 12, 5),
        date(2026, 12, 6),
    )


def test_parse_date_range_recent_past_date_stays_this_year():
    # 一覧に残っている直近の過去のイベントを1年後のイベントにしない
    assert parse_date_range("11月10日", TODAY) == (date(2026, 11, 10), date(2026, 11, 10))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1/31(土)〜2日", (date(2027, 1, 31), date(2027, 2, 2))),
        ("2026.12.30 - 01", (date(2026, 12, 30), date(2027, 1, 1))),
    ],
)
def test_parse_date_range_bare_day_crosses_month(text, expected):
    assert parse_date_range(text, TODAY) == expected


def test_jsonld_utc_datetime_is_converted_to_japan_date():
    html = (
        '<script type="application/ld+json">{"@type": "Event", "name": "UTC",'
        ' "startDate": "2026-12-04T15:00:00Z", "endDate": "2026-12-05T09:00:00+00:00"}</script>'
    )

    [event] = parse_events(html, "https://example.com/", CONFIG, TODAY)

    assert (event.start_date, event.end_date) == (date(2026, 12, 5), date(2026, 12, 5))


def test_item_text_is_used_when_date_selector_matches_nothing():
    html = (
        '<article class="event"><h2><a href="/e">ブログ形式</a></h2>'
        "<p>開催日：12月5日</p></article>"
    )

    [event] = parse_events(html, "https://example.com/", CONFIG, TODAY)

    assert event.start_date == date(2026, 12, 5)


def test_jsonld_events_inside_item_list_are_found():
    html = (
        '<script type="application/ld+json">{"@type": "ItemList", "itemListElement": ['
        '{"@type": "ListItem", "item": {"@type": "Event", "name": "入れ子", "startDate": "2026-12-05"}}'
        "]}</script>"
    )

    [event] = parse_events(html, "https://example.com/", CONFIG, TODAY)

    assert event.name == "入れ子"


def test_parse_date_range_leap_day_next_year():
    assert parse_date_range("2/29〜3/1", date(2027, 12, 10)) == (
        date(2028, 2, 29),
        date(2028, 3, 1),
    )
