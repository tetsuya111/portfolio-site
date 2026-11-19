import datetime as dt
import time

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Actress, Event, EventSource, Venue

pytestmark = pytest.mark.django_db
D = dt.date


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def data():
    akiba = Venue.objects.create(
        name="秋葉原ホール",
        address="東京都千代田区",
        prefecture="東京都",
        latitude=35.7,
        longitude=139.77,
    )
    namba = Venue.objects.create(name="なんばホール", address="", prefecture="大阪府")
    hanako = Actress.objects.create(name="山田花子")
    misaki = Actress.objects.create(name="佐藤美咲")
    e1 = Event.objects.create(
        title="サイン会",
        start_date=D(2026, 12, 3),
        venue=akiba,
        summary="新作",
        url="https://x.example/1",
    )
    e1.actresses.add(hanako)
    EventSource.objects.create(event=e1, source_name="a", source_url="https://a.example/1")
    EventSource.objects.create(event=e1, source_name="b", source_url="https://b.example/1")
    e2 = Event.objects.create(
        title="撮影会",
        start_date=D(2026, 12, 1),
        end_date=D(2026, 12, 5),
        venue=namba,
        note="整理券",
    )
    e2.actresses.add(misaki)
    e3 = Event.objects.create(title="トークライブ", start_date=D(2026, 12, 10), venue=akiba)
    e3.actresses.add(hanako, misaki)
    return {"e1": e1, "e2": e2, "e3": e3, "akiba": akiba, "namba": namba}


def titles(res):
    return [e["title"] for e in res.json()["results"]]


def test_list_ordered_by_date(client, data):
    res = client.get("/api/events/")
    assert res.status_code == 200
    assert titles(res) == ["撮影会", "サイン会", "トークライブ"]
    first = res.json()["results"][1]
    assert first["actresses"] == ["山田花子"]
    assert first["venue"] == {
        "id": data["akiba"].id,
        "name": "秋葉原ホール",
        "prefecture": "東京都",
    }


@pytest.mark.parametrize(
    ("q", "expected"),
    [
        ("サイン", ["サイン会"]),
        ("佐藤", ["撮影会", "トークライブ"]),
        ("なんば", ["撮影会"]),
        ("整理券", ["撮影会"]),
        ("新作", ["サイン会"]),
        ("該当なし", []),
    ],
)
def test_keyword_search(client, data, q, expected):
    assert titles(client.get("/api/events/", {"q": q})) == expected


def test_period_overlap(client, data):
    res = client.get("/api/events/", {"from": "2026-12-04", "to": "2026-12-09"})
    assert titles(res) == ["撮影会"]
    res = client.get("/api/events/", {"from": "2026-12-03"})
    assert titles(res) == ["撮影会", "サイン会", "トークライブ"]
    res = client.get("/api/events/", {"to": "2026-12-02"})
    assert titles(res) == ["撮影会"]


def test_prefecture(client, data):
    assert titles(client.get("/api/events/", {"prefecture": "東京都"})) == [
        "サイン会",
        "トークライブ",
    ]


@pytest.mark.parametrize(
    "params", [{"from": "2026-13-01"}, {"to": "abc"}, {"from": "2026-12-05", "to": "2026-12-01"}]
)
def test_invalid_dates_return_400(client, data, params):
    assert client.get("/api/events/", params).status_code == 400


def test_pagination(client):
    Event.objects.bulk_create(
        Event(
            title=f"e{i}",
            normalized_title=f"e{i}",
            start_date=D(2026, 12, 1),
            end_date=D(2026, 12, 1),
        )
        for i in range(25)
    )
    body = client.get("/api/events/").json()
    assert body["count"] == 25
    assert len(body["results"]) == 20
    assert len(client.get("/api/events/", {"page": 2}).json()["results"]) == 5


def test_detail(client, data):
    body = client.get(f"/api/events/{data['e1'].id}/").json()
    assert body["title"] == "サイン会"
    assert body["url"] == "https://x.example/1"
    assert body["summary"] == "新作"
    assert body["venue"]["address"] == "東京都千代田区"
    assert body["venue"]["latitude"] == 35.7
    assert [s["source_url"] for s in body["sources"]] == [
        "https://a.example/1",
        "https://b.example/1",
    ]


def test_detail_not_found(client):
    assert client.get("/api/events/999/").status_code == 404


def test_write_methods_are_not_allowed(client, data):
    assert client.post("/api/events/", {"title": "x"}).status_code == 405
    assert client.delete(f"/api/events/{data['e1'].id}/").status_code == 405


def test_map_venues(client, data):
    res = client.get("/api/map/venues/", {"from": "2026-12-02", "to": "2026-12-04"})
    assert res.status_code == 200
    venues = res.json()
    # 会場は期間内の最初のイベントの日付順（撮影会 12/1〜 → サイン会 12/3）
    assert [v["name"] for v in venues] == ["なんばホール", "秋葉原ホール"]
    assert [e["title"] for e in venues[1]["events"]] == ["サイン会"]
    assert venues[1]["latitude"] == 35.7
    assert venues[0]["latitude"] is None


def test_map_default_period_is_next_30_days(client):
    venue = Venue.objects.create(name="v", address="")
    today = timezone.localdate()
    Event.objects.create(title="soon", start_date=today + dt.timedelta(days=3), venue=venue)
    Event.objects.create(title="later", start_date=today + dt.timedelta(days=60), venue=venue)
    venues = client.get("/api/map/venues/").json()
    assert [e["title"] for e in venues[0]["events"]] == ["soon"]


@pytest.mark.parametrize(
    "params",
    [
        {"from": "2026-01-01", "to": "2027-12-31"},
        {"from": "x"},
        {"from": "2026-12-05", "to": "2026-12-01"},
    ],
)
def test_map_invalid_period(client, params):
    assert client.get("/api/map/venues/", params).status_code == 400


def test_search_performance(client):
    venue = Venue.objects.create(name="会場", address="", prefecture="東京都")
    Event.objects.bulk_create(
        Event(
            title=f"イベント{i}",
            normalized_title=f"イベント{i}",
            start_date=D(2026, 12, 1) + dt.timedelta(days=i % 60),
            end_date=D(2026, 12, 1) + dt.timedelta(days=i % 60),
            venue=venue,
        )
        for i in range(1000)
    )
    started = time.perf_counter()
    res = client.get("/api/events/", {"q": "イベント", "from": "2026-12-01", "to": "2027-01-31"})
    assert res.status_code == 200
    assert time.perf_counter() - started < 1.0
