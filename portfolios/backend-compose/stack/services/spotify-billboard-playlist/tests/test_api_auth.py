from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.sessions import Session
from tests.conftest import ORIGIN


def _login(client) -> str:
    res = client.get("/auth/login")
    assert res.status_code in (302, 307)
    return parse_qs(urlsplit(res.headers["location"]).query)["state"][0]


def test_login_redirects_and_sets_state(client):
    res = client.get("/auth/login")
    assert res.status_code in (302, 307)
    assert res.headers["location"].startswith("https://accounts.spotify.com/authorize")
    cookie = res.headers["set-cookie"]
    assert "oauth_state=" in cookie
    assert "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()
    state = parse_qs(urlsplit(res.headers["location"]).query)["state"][0]
    assert len(state) >= 32
    assert client.cookies.get("oauth_state") == state


def test_login_without_client_id_500(client, settings):
    object.__setattr__(settings, "spotify_client_id", "")
    res = client.get("/auth/login")
    assert res.status_code == 500


def test_callback_state_mismatch_400(client, sessions):
    _login(client)
    res = client.get("/auth/callback", params={"code": "good-code", "state": "wrong"})
    assert res.status_code == 400
    assert "sid" not in client.cookies


def test_callback_missing_state_cookie_400(client):
    res = client.get("/auth/callback", params={"code": "good-code", "state": "abc"})
    assert res.status_code == 400


def test_callback_spotify_error_param_400(client):
    state = _login(client)
    res = client.get("/auth/callback", params={"error": "access_denied", "state": state})
    assert res.status_code == 400


def test_callback_bad_code_400(client):
    state = _login(client)
    res = client.get("/auth/callback", params={"code": "bad", "state": state})
    assert res.status_code == 400


def test_callback_success_sets_sid_and_redirects(client, sessions):
    state = _login(client)
    res = client.get("/auth/callback", params={"code": "good-code", "state": state})
    assert res.status_code in (302, 307)
    assert res.headers["location"] == ORIGIN + "/"
    sid = client.cookies.get("sid")
    assert sid
    assert sessions.get(sid).display_name == "Tetsu"
    assert "oauth_state" not in client.cookies


def test_me_unauthenticated(client):
    assert client.get("/api/me").json() == {"authenticated": False}


def test_me_authenticated(client, logged_in, sessions):
    body = client.get("/api/me").json()
    assert body == {
        "authenticated": True,
        "id": "u1",
        "display_name": "Tetsu",
        "csrf_token": sessions.get(logged_in).csrf_token,
    }
    assert "access" not in str(body)


def test_logout_clears_session(client, logged_in, sessions):
    res = client.post("/auth/logout", headers={"Origin": ORIGIN})
    assert res.status_code == 204
    assert sessions.get(logged_in) is None
    assert client.get("/api/me").json() == {"authenticated": False}


def test_logout_rejects_foreign_origin(client, logged_in, sessions):
    res = client.post("/auth/logout", headers={"Origin": "https://evil.example"})
    assert res.status_code == 403
    assert sessions.get(logged_in) is not None


def test_callback_profile_without_id_400(client, spotify, sessions):
    async def no_id(access_token):
        return {"display_name": "No Id"}

    spotify.me = no_id
    state = _login(client)
    res = client.get("/auth/callback", params={"code": "good-code", "state": state})
    assert res.status_code == 400
    assert "sid" not in client.cookies


SITE = "https://site.example"
PREFIX = "/apps/spotify-billboard-playlist"


def _cookie_header(res, name: str) -> str:
    return next(h for h in res.headers.get_list("set-cookie") if h.startswith(name + "="))


@pytest.fixture
def site_client(db, fetcher, spotify, sessions):
    """FRONTEND_URL にパスがある構成（サイトの /apps/<slug>/ の下で同一オリジンにする）。"""
    settings = Settings(
        spotify_client_id="cid",
        spotify_client_secret="secret",
        redirect_uri=SITE + PREFIX + "/auth/callback",
        frontend_url=SITE + PREFIX,
        public_path=PREFIX,
        cookie_secure=True,
    )
    app = create_app(settings, db, fetcher, spotify, sessions)
    return TestClient(app, base_url=SITE, follow_redirects=False, headers={"Origin": SITE})


def test_site_cookies_use_public_path(site_client, sessions):
    res = site_client.get("/auth/login")
    state_cookie = _cookie_header(res, "oauth_state")
    assert f"Path={PREFIX}/auth" in state_cookie
    assert "Secure" in state_cookie
    state = parse_qs(urlsplit(res.headers["location"]).query)["state"][0]

    res = site_client.get(
        "/auth/callback",
        params={"code": "good-code", "state": state},
        headers={"Cookie": f"oauth_state={state}"},
    )
    assert res.headers["location"] == SITE + PREFIX + "/"
    assert f"Path={PREFIX}/auth" in _cookie_header(res, "oauth_state")
    sid_cookie = _cookie_header(res, "sid")
    assert f"Path={PREFIX}/" in sid_cookie
    assert "Path=/;" not in sid_cookie
    sid = sid_cookie.split(";")[0].split("=", 1)[1]

    token = sessions.get(sid).csrf_token
    res = site_client.post(
        "/auth/logout", headers={"Cookie": f"sid={sid}", "X-CSRF-Token": token}
    )
    assert res.status_code == 204
    assert f"Path={PREFIX}/" in _cookie_header(res, "sid")
    assert sessions.get(sid) is None


def test_site_rejects_foreign_origin(site_client, sessions):
    sid = sessions.create(Session("access", "refresh", 9_999_999_999.0, "u1", "Tetsu"))
    res = site_client.post(
        "/auth/logout",
        headers={
            "Origin": "https://evil.example",
            "Cookie": f"sid={sid}",
            "X-CSRF-Token": sessions.get(sid).csrf_token,
        },
    )
    assert res.status_code == 403
    assert sessions.get(sid) is not None
