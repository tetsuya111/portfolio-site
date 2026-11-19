from datetime import date

import pytest

from catalog.collector.importer import import_cosplayer, import_event
from catalog.collector.normalizer import NormalizedLocation, RuleBasedNormalizer
from catalog.collector.parsers.cosplayers import CosplayerItem
from catalog.collector.parsers.events import EventItem
from catalog.models import Cosplayer, Event, FetchedPage, Venue

pytestmark = pytest.mark.django_db


class CountingNormalizer:
    def __init__(self):
        self.calls = []
        self.rule = RuleBasedNormalizer()

    def normalize(self, raw):
        self.calls.append(raw)
        return self.rule.normalize(raw)


def page(url):
    return FetchedPage.objects.create(url=url, kind="event", status_code=200)


def item(name="コスプレフェスタ冬", start=date(2026, 12, 5), end=None, **kwargs):
    defaults = {"url": "", "location": "東京ビッグサイト", "notes": ""}
    defaults.update(kwargs)
    return EventItem(name=name, start_date=start, end_date=end or start, **defaults)


def test_new_event_is_created_with_venue():
    event, created = import_event(item(), page("https://a.example/1"), CountingNormalizer())

    assert created is True
    assert event.venue.name == "東京ビッグサイト"
    assert event.venue.prefecture == "東京都"
    assert event.location_raw == "東京ビッグサイト"
    assert event.source_url == "https://a.example/1"
    assert list(event.sources.values_list("url", flat=True)) == ["https://a.example/1"]


def test_similar_event_on_same_day_is_merged():
    normalizer = CountingNormalizer()
    first, _ = import_event(item(notes=""), page("https://a.example/1"), normalizer)

    merged, created = import_event(
        item(name="コスプレ フェスタ 冬！", notes="撮影OK", url="https://official.example/"),
        page("https://b.example/2"),
        normalizer,
    )

    assert created is False
    assert merged.pk == first.pk
    assert Event.objects.count() == 1
    merged.refresh_from_db()
    assert merged.notes == "撮影OK"
    assert merged.url == "https://official.example/"
    assert merged.source_url == "https://a.example/1"
    assert merged.sources.count() == 2


def test_similar_event_on_other_day_is_separate():
    normalizer = CountingNormalizer()
    import_event(item(), page("https://a.example/1"), normalizer)

    _, created = import_event(
        item(start=date(2026, 12, 12)), page("https://b.example/2"), normalizer
    )

    assert created is True
    assert Event.objects.count() == 2


def test_different_event_on_same_day_is_separate():
    normalizer = CountingNormalizer()
    import_event(item(name="ホココス"), page("https://a.example/1"), normalizer)

    _, created = import_event(item(name="となコス"), page("https://b.example/2"), normalizer)

    assert created is True


def test_import_event_fixes_end_before_start():
    event, _ = import_event(
        item(start=date(2026, 12, 6), end=date(2026, 12, 5)),
        page("https://a.example/1"),
        CountingNormalizer(),
    )

    assert event.end_date == date(2026, 12, 6)


def test_same_location_is_normalized_once_and_venue_is_shared():
    normalizer = CountingNormalizer()
    first, _ = import_event(item(name="イベントA"), page("https://a.example/1"), normalizer)
    second, _ = import_event(item(name="全然違うB"), page("https://a.example/2"), normalizer)

    assert normalizer.calls == ["東京ビッグサイト"]
    assert first.venue_id == second.venue_id
    assert Venue.objects.count() == 1


def test_event_without_location_has_no_venue():
    event, _ = import_event(item(location=""), page("https://a.example/1"), CountingNormalizer())

    assert event.venue is None


def test_venue_address_is_filled_later():
    Venue.objects.create(name="某ホール", prefecture="", address="")

    class Fixed:
        def normalize(self, raw):
            return NormalizedLocation("某ホール", "大阪府", "大阪府大阪市1-1")

    event, _ = import_event(item(location="某ホール"), page("https://a.example/1"), Fixed())

    assert event.venue.prefecture == "大阪府"
    assert event.venue.address == "大阪府大阪市1-1"


def cosplayer(name="うえ", **kwargs):
    return CosplayerItem(name=name, **kwargs)


def test_new_cosplayer_is_created():
    person, created = import_cosplayer(
        cosplayer(sns_links=["https://x.com/ue"], description="説明"), page("https://w.example/ue")
    )

    assert created is True
    assert person.sns_links == ["https://x.com/ue"]
    assert person.source_url == "https://w.example/ue"


def test_similar_cosplayer_is_merged():
    import_cosplayer(
        cosplayer(name="コスプレイヤー太郎", sns_links=["https://x.com/taro"]),
        page("https://w.example/1"),
    )

    person, created = import_cosplayer(
        cosplayer(
            name="コスプレイヤー 太郎",
            sns_links=["https://x.com/taro", "https://www.instagram.com/taro/"],
            career="2015年から活動",
        ),
        page("https://w.example/2"),
    )

    assert created is False
    assert Cosplayer.objects.count() == 1
    person.refresh_from_db()
    assert person.sns_links == ["https://x.com/taro", "https://www.instagram.com/taro/"]
    assert person.career == "2015年から活動"
    assert person.sources.count() == 2


def test_cosplayer_below_threshold_is_separate():
    # 9文字中1文字違い → 類似度 0.889（0.9 未満）
    import_cosplayer(cosplayer(name="あいうえおかきくけ"), page("https://w.example/1"))

    _, created = import_cosplayer(cosplayer(name="あいうえおかきくこ"), page("https://w.example/2"))

    assert created is True
    assert Cosplayer.objects.count() == 2


def test_unsafe_sns_links_are_not_saved():
    person, _ = import_cosplayer(
        cosplayer(sns_links=["javascript:alert(1)", "https://x.com/ok"]),
        page("https://w.example/1"),
    )

    assert person.sns_links == ["https://x.com/ok"]


def test_cosplayer_exactly_at_threshold_with_length_difference_is_merged():
    # 10文字と9文字（1文字削除）→ 類似度ちょうど 0.9
    import_cosplayer(cosplayer(name="あいうえおかきくけこ"), page("https://w.example/1"))

    _, created = import_cosplayer(cosplayer(name="あいうえおかきくけ"), page("https://w.example/2"))

    assert created is False
