from urllib.parse import parse_qs, urlsplit

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


def test_me_authenticated(client, logged_in):
    body = client.get("/api/me").json()
    assert body == {"authenticated": True, "id": "u1", "display_name": "Tetsu"}
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
