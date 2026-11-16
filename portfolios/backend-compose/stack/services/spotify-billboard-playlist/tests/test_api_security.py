"""CSRF 対策・ログイン必須化・回数制限・セッション Cookie の検証。"""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.ratelimit import RateLimiter
from app.sessions import SESSION_IDLE_TIMEOUT, SESSION_MAX_AGE, Session, SessionStore
from tests.conftest import ORIGIN
from tests.test_api_auth import _login

CHART = ("/api/charts", {"url": "https://billboard.mryogaku.com/php/chart.php?date=2025-11-15"})
PLAYLIST = ("/api/playlists", {"name": "x", "tracks": [{"title": "t", "artist": "a"}]})
LOGOUT = ("/auth/logout", None)
STATE_CHANGING = [CHART, PLAYLIST, LOGOUT]


def _post(client, endpoint, headers=None):
    path, payload = endpoint
    return client.post(path, json=payload, headers=headers)


# ---- /api/charts のログイン必須化と回数制限 ----


def test_post_chart_requires_login_401(client, db):
    res = _post(client, CHART)
    assert res.status_code == 401
    assert db.get_source(1) is None


def test_post_chart_rate_limited_429(settings, db, fetcher, spotify, sessions):
    app = create_app(settings, db, fetcher, spotify, sessions, chart_limiter=RateLimiter(1, 60))
    client = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})
    sid = sessions.create(Session("access", "refresh", 9_999_999_999.0, "u1", "Tetsu"))
    client.cookies.set("sid", sid)
    client.headers["X-CSRF-Token"] = sessions.get(sid).csrf_token
    assert _post(client, CHART).status_code == 200
    assert _post(client, CHART).status_code == 429
    assert db.get_source(1) is not None
    assert db.get_source(2) is None  # 拒否したリクエストは DB に行を作らない


# ---- Origin / Sec-Fetch-Site（fail-closed） ----


@pytest.mark.parametrize("endpoint", STATE_CHANGING)
def test_post_without_origin_rejected(client, logged_in, endpoint):
    del client.headers["Origin"]
    assert _post(client, endpoint).status_code == 403


@pytest.mark.parametrize("endpoint", STATE_CHANGING)
def test_post_without_origin_same_origin_fetch_site_allowed(client, logged_in, endpoint):
    del client.headers["Origin"]
    res = _post(client, endpoint, headers={"Sec-Fetch-Site": "same-origin"})
    assert res.status_code != 403


@pytest.mark.parametrize("fetch_site", ["same-site", "cross-site", "none"])
def test_post_other_fetch_site_rejected(client, logged_in, fetch_site):
    del client.headers["Origin"]
    assert _post(client, CHART, headers={"Sec-Fetch-Site": fetch_site}).status_code == 403


def test_post_null_origin_rejected(client, logged_in):
    assert _post(client, CHART, headers={"Origin": "null"}).status_code == 403


# ---- CSRF トークン ----


@pytest.mark.parametrize("endpoint", STATE_CHANGING)
def test_post_missing_csrf_token_403(client, logged_in, sessions, endpoint):
    del client.headers["X-CSRF-Token"]
    assert _post(client, endpoint).status_code == 403
    assert sessions.get(logged_in) is not None


@pytest.mark.parametrize("endpoint", STATE_CHANGING)
def test_post_wrong_csrf_token_403(client, logged_in, sessions, endpoint):
    assert _post(client, endpoint, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert sessions.get(logged_in) is not None


def test_logout_without_session_needs_no_token(client):
    assert _post(client, LOGOUT).status_code == 204


def test_me_returns_csrf_token(client, logged_in, sessions):
    body = client.get("/api/me").json()
    assert body["csrf_token"] == sessions.get(logged_in).csrf_token


# ---- セッションの期限と Cookie ----


@pytest.mark.parametrize("elapsed", [SESSION_IDLE_TIMEOUT + 1, SESSION_MAX_AGE + 1])
def test_me_expired_session_unauthenticated(settings, db, fetcher, spotify, elapsed):
    now = [1000.0]
    sessions = SessionStore(clock=lambda: now[0])
    client = TestClient(create_app(settings, db, fetcher, spotify, sessions), base_url=ORIGIN)
    client.cookies.set("sid", sessions.create(Session("a", "r", 9e9, "u1", "Tetsu")))
    assert client.get("/api/me").json()["authenticated"] is True
    now[0] += elapsed
    assert client.get("/api/me").json() == {"authenticated": False}


def test_callback_session_cookie_max_age(client):
    state = _login(client)
    res = client.get("/auth/callback", params={"code": "good-code", "state": state})
    sid_cookie = next(c for c in res.headers.get_list("set-cookie") if c.startswith("sid="))
    assert f"Max-Age={SESSION_MAX_AGE}" in sid_cookie
    assert "Secure" not in sid_cookie


def test_cookie_secure_follows_settings(db, fetcher, spotify, sessions):
    settings = Settings(spotify_client_id="cid", spotify_client_secret="s", cookie_secure=True)
    client = TestClient(
        create_app(settings, db, fetcher, spotify, sessions),
        base_url="https://127.0.0.1:3000",
        follow_redirects=False,
    )
    res = client.get("/auth/login")
    assert "Secure" in res.headers["set-cookie"]


def test_session_without_csrf_token_rejected(client, logged_in, sessions):
    sessions.get(logged_in).csrf_token = ""
    assert _post(client, CHART, headers={"X-CSRF-Token": ""}).status_code == 403
