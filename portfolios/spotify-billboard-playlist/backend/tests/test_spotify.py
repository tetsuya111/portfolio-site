import asyncio
import base64
import json
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.config import Settings
from app.sessions import Session
from app.spotify import SpotifyClient, SpotifyError, TrackQuery, primary_artist

SETTINGS = Settings(spotify_client_id="cid", spotify_client_secret="csecret")
NOW = 1_000_000.0


class FakeSpotify:
    """accounts.spotify.com と api.spotify.com をまとめて模倣する。"""

    def __init__(self, catalog=None):
        self.catalog = catalog or {}  # 検索クエリに含まれる曲名(小文字) -> uri
        self.requests: list[httpx.Request] = []
        self.searches: list[str] = []
        self.added: list[list[str]] = []
        self.status_queue: list[httpx.Response] = []
        self.token_requests: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status_queue:
            return self.status_queue.pop(0)
        path = request.url.path
        if request.url.host == "accounts.spotify.com":
            form = parse_qs(request.content.decode())
            self.token_requests.append(
                {"form": form, "auth": request.headers.get("Authorization")}
            )
            body = {"access_token": "new-access", "expires_in": 3600}
            if form["grant_type"] == ["authorization_code"]:
                body["refresh_token"] = "refresh-1"
            return httpx.Response(200, json=body)
        if path == "/v1/me":
            return httpx.Response(200, json={"id": "u1", "display_name": "Tetsu"})
        if path == "/v1/search":
            q = request.url.params["q"]
            self.searches.append(q)
            items = [
                {"uri": uri} for key, uri in self.catalog.items() if key in q.lower()
            ]
            return httpx.Response(200, json={"tracks": {"items": items[:1]}})
        if path == "/v1/me/playlists":
            return httpx.Response(
                201,
                json={"id": "pl1", "external_urls": {"spotify": "https://open.spotify.com/playlist/pl1"}},
            )
        if path == "/v1/playlists/pl1/items":
            self.added.append(json.loads(request.content)["uris"])
            return httpx.Response(201, json={"snapshot_id": "s"})
        return httpx.Response(404)


def _client(fake: FakeSpotify, sleeps: list[float] | None = None) -> SpotifyClient:
    async def fake_sleep(seconds: float) -> None:
        if sleeps is not None:
            sleeps.append(seconds)

    return SpotifyClient(
        SETTINGS,
        transport=httpx.MockTransport(fake.handler),
        sleep=fake_sleep,
        clock=lambda: NOW,
    )


def _session(expires_at: float = NOW + 3600) -> Session:
    return Session("access", "refresh", expires_at, "u1", "Tetsu")


def run(coro):
    return asyncio.run(coro)


def test_authorize_url_params():
    url = _client(FakeSpotify()).authorize_url("st4te")
    parts = urlsplit(url)
    assert parts.netloc == "accounts.spotify.com"
    assert parts.path == "/authorize"
    q = parse_qs(parts.query)
    assert q["client_id"] == ["cid"]
    assert q["response_type"] == ["code"]
    assert q["scope"] == ["playlist-modify-private"]
    assert q["state"] == ["st4te"]
    assert q["redirect_uri"] == ["http://127.0.0.1:3000/auth/callback"]


def test_exchange_code_uses_basic_auth():
    fake = FakeSpotify()
    tokens = run(_client(fake).exchange_code("the-code"))
    assert tokens.access_token == "new-access"
    assert tokens.refresh_token == "refresh-1"
    assert tokens.expires_at == NOW + 3600
    sent = fake.token_requests[0]
    assert sent["auth"] == "Basic " + base64.b64encode(b"cid:csecret").decode()
    assert sent["form"]["code"] == ["the-code"]
    assert sent["form"]["redirect_uri"] == ["http://127.0.0.1:3000/auth/callback"]


def test_refresh_keeps_old_refresh_token_when_absent():
    tokens = run(_client(FakeSpotify()).refresh("refresh-old"))
    assert tokens.refresh_token == "refresh-old"


def test_me():
    assert run(_client(FakeSpotify()).me("access"))["display_name"] == "Tetsu"


@pytest.mark.parametrize(
    ("artist", "expected"),
    [
        ("Taylor Swift", "Taylor Swift"),
        ("Morgan Wallen Featuring Tate McRae", "Morgan Wallen"),
        ("Loe Shimmy & Don Toliver", "Loe Shimmy"),
        ("HUNTR/X: EJAE, Audrey Nuna & REI AMI", "HUNTR/X"),
        ("Lady Gaga, Bruno Mars", "Lady Gaga"),
        ("Rosé X Bruno Mars", "Rosé"),
        ("", ""),
    ],
)
def test_primary_artist(artist, expected):
    assert primary_artist(artist) == expected


def test_build_playlist_skips_not_found_keeps_order():
    fake = FakeSpotify({"song a": "spotify:track:a", "song c": "spotify:track:c"})
    tracks = [
        TrackQuery("Song A", "Artist"),
        TrackQuery("Song B", "Artist"),
        TrackQuery("Song C", "Artist"),
    ]
    result = run(_client(fake).build_playlist(_session(), "My list", tracks))
    assert result.playlist_id == "pl1"
    assert result.url == "https://open.spotify.com/playlist/pl1"
    assert result.added == 2
    assert result.not_found == [TrackQuery("Song B", "Artist")]
    assert fake.added == [["spotify:track:a", "spotify:track:c"]]
    create = next(r for r in fake.requests if r.url.path == "/v1/me/playlists")
    assert json.loads(create.content)["public"] is False
    assert json.loads(create.content)["name"] == "My list"
    assert create.headers["Authorization"] == "Bearer access"


def test_fallback_query_used():
    fake = FakeSpotify({"golden huntr/x": "spotify:track:g"})
    result = run(
        _client(fake).build_playlist(
            _session(), "x", [TrackQuery("Golden", "HUNTR/X: EJAE, Audrey Nuna & REI AMI")]
        )
    )
    assert result.added == 1
    assert fake.searches == ['track:"Golden" artist:"HUNTR/X"', "Golden HUNTR/X"]


def test_query_strips_double_quotes():
    fake = FakeSpotify()
    run(_client(fake).build_playlist(_session(), "x", [TrackQuery('Say "Hi"', 'A"B')]))
    assert fake.searches[0] == 'track:"Say Hi" artist:"AB"'


def test_items_added_in_chunks_of_100():
    catalog = {f"song {i:03d}": f"spotify:track:{i}" for i in range(150)}
    fake = FakeSpotify(catalog)
    tracks = [TrackQuery(f"Song {i:03d}", "A") for i in range(150)]
    result = run(_client(fake).build_playlist(_session(), "x", tracks))
    assert result.added == 150
    assert [len(chunk) for chunk in fake.added] == [100, 50]
    assert fake.added[0][0] == "spotify:track:0"
    assert fake.added[1][-1] == "spotify:track:149"


def test_no_tracks_found_still_creates_without_adding():
    fake = FakeSpotify()
    result = run(_client(fake).build_playlist(_session(), "x", [TrackQuery("Nope", "A")]))
    assert result.added == 0
    assert fake.added == []


def test_retry_after_on_429():
    fake = FakeSpotify()
    fake.status_queue = [
        httpx.Response(429, headers={"Retry-After": "2"}),
        httpx.Response(429, headers={"Retry-After": "999"}),
    ]
    sleeps: list[float] = []
    assert run(_client(fake, sleeps).me("access"))["id"] == "u1"
    assert sleeps == [2.0, 30.0]


def test_429_gives_up_after_3_retries():
    fake = FakeSpotify()
    fake.status_queue = [httpx.Response(429, headers={"Retry-After": "1"}) for _ in range(4)]
    sleeps: list[float] = []
    with pytest.raises(SpotifyError) as exc:
        run(_client(fake, sleeps).me("access"))
    assert exc.value.status == 429
    assert len(sleeps) == 3


def test_error_status_raises_spotify_error():
    fake = FakeSpotify()
    fake.status_queue = [httpx.Response(403, json={"error": {"message": "Forbidden"}})]
    with pytest.raises(SpotifyError) as exc:
        run(_client(fake).me("access"))
    assert exc.value.status == 403
    assert "Forbidden" in str(exc.value)


def test_refreshes_expired_token():
    fake = FakeSpotify({"song a": "spotify:track:a"})
    session = _session(expires_at=NOW + 30)  # 60秒の余裕を切っている
    run(_client(fake).build_playlist(session, "x", [TrackQuery("Song A", "A")]))
    assert session.access_token == "new-access"
    assert session.refresh_token == "refresh"
    assert fake.token_requests[0]["form"]["grant_type"] == ["refresh_token"]
    api_calls = [r for r in fake.requests if r.url.host == "api.spotify.com"]
    assert all(r.headers["Authorization"] == "Bearer new-access" for r in api_calls)


def test_refreshes_on_401_once():
    fake = FakeSpotify({"song a": "spotify:track:a"})
    fake.status_queue = [httpx.Response(401)]
    session = _session()
    result = run(_client(fake).build_playlist(session, "x", [TrackQuery("Song A", "A")]))
    assert result.added == 1
    assert session.access_token == "new-access"


def test_search_failure_aborts_without_creating_playlist():
    fake = FakeSpotify({"song a": "spotify:track:a"})
    original = fake.handler

    def handler(request):
        if request.url.path == "/v1/search" and "Song B" in request.url.params["q"]:
            fake.requests.append(request)
            return httpx.Response(500)
        return original(request)

    client = SpotifyClient(SETTINGS, transport=httpx.MockTransport(handler), clock=lambda: NOW)
    tracks = [TrackQuery(f"Song {c}", "A") for c in "ABCDEFGH"]
    with pytest.raises(SpotifyError) as exc:
        run(client.build_playlist(_session(), "x", tracks))
    assert exc.value.status == 500
    assert not any(r.url.path == "/v1/me/playlists" for r in fake.requests)
    # 失敗後も他の検索は完了まで待たれている（閉じたクライアントで走り続けない）
    searched = {r.url.params["q"] for r in fake.requests if r.url.path == "/v1/search"}
    assert any("Song H" in q for q in searched)
