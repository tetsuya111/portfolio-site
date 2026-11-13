import pytest

from app.spotify import SpotifyError, TrackQuery
from tests.conftest import ORIGIN

TRACKS = [
    {"title": "The Fate Of Ophelia", "artist": "Taylor Swift"},
    {"title": "Golden", "artist": "HUNTR/X"},
]


def test_create_playlist_201(client, logged_in, spotify):
    res = client.post(
        "/api/playlists",
        json={"name": "Billboard Hot 100 (2025-11-15)", "tracks": TRACKS},
        headers={"Origin": ORIGIN},
    )
    assert res.status_code == 201
    assert res.json() == {
        "playlist_id": "pl1",
        "url": "https://open.spotify.com/playlist/pl1",
        "added": 1,
        "not_found": [{"title": "Golden", "artist": "HUNTR/X"}],
    }
    name, tracks = spotify.built[0]
    assert name == "Billboard Hot 100 (2025-11-15)"
    assert tracks[0] == TrackQuery("The Fate Of Ophelia", "Taylor Swift")


def test_create_playlist_unauthenticated_401(client, spotify):
    res = client.post("/api/playlists", json={"name": "x", "tracks": TRACKS})
    assert res.status_code == 401
    assert spotify.built == []


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "x", "tracks": []},
        {"name": "x", "tracks": [{"title": "t", "artist": "a"}] * 101},
        {"name": "", "tracks": TRACKS},
        {"name": "x" * 101, "tracks": TRACKS},
        {"name": "x", "tracks": [{"title": "t" * 201, "artist": "a"}]},
        {"name": "x", "tracks": [{"title": "", "artist": "a"}]},
    ],
)
def test_create_playlist_validation_422(client, logged_in, payload):
    assert client.post("/api/playlists", json=payload).status_code == 422


def test_create_playlist_spotify_error_502(client, logged_in, spotify):
    spotify.error = SpotifyError(500, "Spotify API エラー（HTTP 500）")
    res = client.post("/api/playlists", json={"name": "x", "tracks": TRACKS})
    assert res.status_code == 502
    assert res.json()["detail"] == "Spotify API エラー（HTTP 500）"


def test_create_playlist_spotify_unauthorized_logs_out(client, logged_in, spotify, sessions):
    spotify.error = SpotifyError(401, "expired")
    res = client.post("/api/playlists", json={"name": "x", "tracks": TRACKS})
    assert res.status_code == 401
    assert sessions.get(logged_in) is None


def test_create_playlist_rejects_foreign_origin(client, logged_in, spotify):
    res = client.post(
        "/api/playlists",
        json={"name": "x", "tracks": TRACKS},
        headers={"Origin": "https://evil.example"},
    )
    assert res.status_code == 403
    assert spotify.built == []
