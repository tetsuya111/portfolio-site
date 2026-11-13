from app.batch.fetcher import FetchError
from tests.conftest import ORIGIN


def test_post_chart_returns_tracks(client, db):
    res = client.post(
        "/api/charts",
        json={"url": "https://billboard.mryogaku.com/php/chart.php?date=2025-11-15"},
        headers={"Origin": ORIGIN},
    )
    assert res.status_code == 200
    body = res.json()
    first = {"rank": 1, "title": "The Fate Of Ophelia", "artist": "Taylor Swift"}
    assert body["tracks"][0] == first
    assert len(body["tracks"]) == 3
    assert db.get_source(body["id"])["status"] == "done"


def test_post_chart_invalid_url_400(client, db):
    res = client.post("/api/charts", json={"url": "https://example.com/"})
    assert res.status_code == 400
    assert "billboard.mryogaku.com" in res.json()["detail"]
    assert db.get_source(1)["status"] == "failed"


def test_post_chart_too_long_url_422(client):
    res = client.post("/api/charts", json={"url": "https://billboard.mryogaku.com/" + "a" * 2100})
    assert res.status_code == 422


def test_post_chart_fetch_error_502(client, fetcher):
    fetcher.error = FetchError("チャートページの取得に失敗しました（HTTP 500）")
    res = client.post(
        "/api/charts",
        json={"url": "https://billboard.mryogaku.com/php/chart.php?date=2025-11-15"},
    )
    assert res.status_code == 502
    assert "HTTP 500" in res.json()["detail"]


def test_post_rejects_foreign_origin_403(client):
    res = client.post(
        "/api/charts",
        json={"url": "https://billboard.mryogaku.com/"},
        headers={"Origin": "https://evil.example"},
    )
    assert res.status_code == 403


def test_post_allows_same_origin(client):
    res = client.post(
        "/api/charts",
        json={"url": "https://billboard.mryogaku.com/php/dispHot100.php?date=2025-11-15"},
        headers={"Origin": ORIGIN},
    )
    assert res.status_code == 200
