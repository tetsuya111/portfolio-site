from datetime import date, timedelta

import pytest

from catalog.models import Event, FetchedPage, Venue

pytestmark = pytest.mark.django_db


@pytest.fixture
def venues():
    return {
        "bigsight": Venue.objects.create(
            name="東京ビッグサイト", prefecture="東京都", address="東京都江東区"
        ),
        "intex": Venue.objects.create(
            name="インテックス大阪", prefecture="大阪府", address="大阪府大阪市"
        ),
    }


def make_event(name, start, end=None, venue=None, **kwargs):
    return Event.objects.create(
        name=name, start_date=start, end_date=end or start, venue=venue, **kwargs
    )


def names(response):
    return [e["name"] for e in response.json()["results"]]


def test_events_are_ordered_by_start_date(client, venues):
    make_event("後", date(2026, 12, 20))
    make_event("先", date(2026, 12, 1), venue=venues["bigsight"])

    response = client.get("/api/events/")

    assert response.status_code == 200
    assert names(response) == ["先", "後"]
    first = response.json()["results"][0]
    assert first["venue"] == {
        "id": venues["bigsight"].id,
        "name": "東京ビッグサイト",
        "prefecture": "東京都",
        "address": "東京都江東区",
    }
    assert "sources" not in first


def test_keyword_matches_name_venue_and_notes(client, venues):
    make_event("コスプレ祭り", date(2026, 12, 1))
    make_event("撮影会A", date(2026, 12, 2), venue=venues["intex"])
    make_event("撮影会B", date(2026, 12, 3), notes="インテックス近くの会場")
    make_event("撮影会C", date(2026, 12, 4), location_raw="インテックス 2F")
    make_event("無関係", date(2026, 12, 5))

    assert names(client.get("/api/events/", {"q": "祭り"})) == ["コスプレ祭り"]
    assert names(client.get("/api/events/", {"q": "インテックス"})) == [
        "撮影会A",
        "撮影会B",
        "撮影会C",
    ]


def test_period_filter_includes_overlapping_events(client):
    make_event("前にはみ出す", date(2026, 11, 30), date(2026, 12, 2))
    make_event("中", date(2026, 12, 5))
    make_event("後ろにはみ出す", date(2026, 12, 9), date(2026, 12, 11))
    make_event("期間外（前）", date(2026, 11, 1))
    make_event("期間外（後）", date(2026, 12, 20))

    response = client.get("/api/events/", {"from": "2026-12-01", "to": "2026-12-10"})

    assert names(response) == ["前にはみ出す", "中", "後ろにはみ出す"]


def test_prefecture_filter(client, venues):
    make_event("東京", date(2026, 12, 1), venue=venues["bigsight"])
    make_event("大阪", date(2026, 12, 2), venue=venues["intex"])

    assert names(client.get("/api/events/", {"prefecture": "大阪府"})) == ["大阪"]


@pytest.mark.parametrize("params", [{"from": "2026-13-01"}, {"to": "abc"}])
def test_events_invalid_date_returns_400(client, params):
    response = client.get("/api/events/", params)

    assert response.status_code == 400


def test_events_are_paginated_by_20(client):
    for i in range(21):
        make_event(f"イベント{i:02}", date(2026, 12, 1) + timedelta(days=i))

    first = client.get("/api/events/").json()
    second = client.get("/api/events/", {"page": 2}).json()

    assert first["count"] == 21
    assert len(first["results"]) == 20
    assert first["next"]
    assert [e["name"] for e in second["results"]] == ["イベント20"]


def test_event_detail_includes_sources(client):
    event = make_event("詳細", date(2026, 12, 1), source_url="https://a.example/1")
    page = FetchedPage.objects.create(url="https://a.example/1", kind="event", status_code=200)
    event.sources.add(page)

    response = client.get(f"/api/events/{event.id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "詳細"
    assert [s["url"] for s in body["sources"]] == ["https://a.example/1"]
    assert body["sources"][0]["fetched_at"]


def test_event_detail_not_found(client):
    assert client.get("/api/events/999/").status_code == 404


def test_unsafe_urls_are_removed(client):
    event = make_event(
        "危険なリンク", date(2026, 12, 1), url="javascript:alert(1)", source_url="data:text/html,x"
    )

    body = client.get(f"/api/events/{event.id}/").json()

    assert body["url"] == ""
    assert body["source_url"] == ""


def test_write_methods_are_not_allowed(client):
    assert client.post("/api/events/", {"name": "x"}).status_code in (403, 405)


def test_venues_in_period_with_counts(client, venues):
    make_event("BS1", date(2026, 12, 1), venue=venues["bigsight"])
    make_event("BS2", date(2026, 12, 3), venue=venues["bigsight"])
    make_event("BS期間外", date(2027, 2, 1), venue=venues["bigsight"])
    make_event("大阪", date(2026, 12, 5), venue=venues["intex"])
    Venue.objects.create(name="使われない会場")

    response = client.get("/api/venues/", {"from": "2026-12-01", "to": "2026-12-31"})

    assert response.status_code == 200
    body = response.json()
    assert [(v["name"], v["event_count"]) for v in body] == [
        ("東京ビッグサイト", 2),
        ("インテックス大阪", 1),
    ]
    assert [e["name"] for e in body[0]["events"]] == ["BS1", "BS2"]


def test_venues_invalid_date_returns_400(client):
    assert client.get("/api/venues/", {"from": "x"}).status_code == 400


def test_venues_from_after_to_returns_400(client):
    assert client.get("/api/venues/", {"from": "2026-12-10", "to": "2026-12-01"}).status_code == 400
