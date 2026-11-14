from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import Database
from app.main import create_app
from app.sessions import Session, SessionStore
from app.spotify import PlaylistResult, SpotifyError, TokenSet, TrackQuery

FIXTURES = Path(__file__).parent / "fixtures"
HOT_URL = "https://billboard.mryogaku.com/php/dispHot100.php?date=2025-11-15"
ORIGIN = "http://127.0.0.1:3000"


class FakeFetcher:
    def __init__(self, pages=None, error=None):
        self.pages = pages or {}
        self.error = error

    def get(self, url):
        if self.error:
            raise self.error
        return self.pages[url]


class FakeSpotify:
    def __init__(self):
        self.built: list[tuple[str, list[TrackQuery]]] = []
        self.error: SpotifyError | None = None

    def authorize_url(self, state):
        return f"https://accounts.spotify.com/authorize?state={state}"

    async def exchange_code(self, code):
        if code != "good-code":
            raise SpotifyError(400, "invalid_grant")
        return TokenSet("access", "refresh", 9_999_999_999.0)

    async def me(self, access_token):
        return {"id": "u1", "display_name": "Tetsu"}

    async def build_playlist(self, session, name, tracks):
        if self.error:
            raise self.error
        self.built.append((name, tracks))
        return PlaylistResult(
            playlist_id="pl1",
            url="https://open.spotify.com/playlist/pl1",
            added=len(tracks) - 1,
            not_found=tracks[-1:],
        )


@pytest.fixture
def settings():
    return Settings(spotify_client_id="cid", spotify_client_secret="secret")


@pytest.fixture
def fetcher():
    hot = (FIXTURES / "hot100.html").read_text(encoding="utf-8")
    return FakeFetcher({HOT_URL: hot})


@pytest.fixture
def spotify():
    return FakeSpotify()


@pytest.fixture
def sessions():
    return SessionStore()


@pytest.fixture
def db():
    return Database(":memory:")


@pytest.fixture
def client(settings, db, fetcher, spotify, sessions):
    app = create_app(settings, db, fetcher, spotify, sessions)
    # ブラウザと同じく、状態を変えるリクエストには Origin が付く前提にする
    return TestClient(app, base_url=ORIGIN, follow_redirects=False, headers={"Origin": ORIGIN})


@pytest.fixture
def logged_in(client, sessions):
    sid = sessions.create(Session("access", "refresh", 9_999_999_999.0, "u1", "Tetsu"))
    client.cookies.set("sid", sid)
    client.headers["X-CSRF-Token"] = sessions.get(sid).csrf_token
    return sid
