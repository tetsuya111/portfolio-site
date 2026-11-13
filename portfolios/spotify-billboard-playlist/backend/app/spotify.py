"""Spotify Accounts / Web API クライアント。"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.sessions import Session

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"  # noqa: S105 - URLでありシークレットではない
API_BASE = "https://api.spotify.com/v1"
SCOPE = "playlist-modify-private"

TIMEOUT_SECONDS = 10.0
MAX_RETRIES = 3
MAX_RETRY_AFTER_SECONDS = 30.0
REFRESH_MARGIN_SECONDS = 60.0
SEARCH_CONCURRENCY = 5
ADD_CHUNK_SIZE = 100

_ARTIST_SPLIT_RE = re.compile(
    r"\s+(?:featuring|feat\.?|ft\.?|with|x)\s+|\s*[&,:]\s*", re.IGNORECASE
)


class SpotifyError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str
    expires_at: float

    def __repr__(self) -> str:
        return f"TokenSet(expires_at={self.expires_at})"


@dataclass(frozen=True)
class TrackQuery:
    title: str
    artist: str


@dataclass(frozen=True)
class PlaylistResult:
    playlist_id: str
    url: str
    added: int
    not_found: list[TrackQuery]


def primary_artist(artist: str) -> str:
    """共演表記（Featuring・&・, 等）より前の主アーティスト名を返す。"""
    return _ARTIST_SPLIT_RE.split(artist.strip(), maxsplit=1)[0].strip()


def _strip_quotes(text: str) -> str:
    return text.replace('"', "").strip()


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("message"):
            return f"Spotify API エラー（HTTP {response.status_code}）: {error['message']}"
        if body.get("error_description"):
            return f"Spotify 認証エラー（HTTP {response.status_code}）: {body['error_description']}"
    return f"Spotify API エラー（HTTP {response.status_code}）"


def _retry_after(response: httpx.Response) -> float:
    try:
        seconds = float(response.headers.get("Retry-After", "1"))
    except ValueError:
        seconds = 1.0
    return min(max(seconds, 0.0), MAX_RETRY_AFTER_SECONDS)


class SpotifyClient:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._settings = settings
        self._transport = transport
        self._sleep = sleep
        self._clock = clock

    # ---- 認可 ----

    def authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self._settings.spotify_client_id,
                "response_type": "code",
                "redirect_uri": self._settings.redirect_uri,
                "scope": SCOPE,
                "state": state,
            }
        )
        return f"{AUTHORIZE_URL}?{query}"

    async def exchange_code(self, code: str) -> TokenSet:
        return await self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._settings.redirect_uri,
            },
            fallback_refresh_token="",
        )

    async def refresh(self, refresh_token: str) -> TokenSet:
        return await self._token_request(
            {"grant_type": "refresh_token", "refresh_token": refresh_token},
            fallback_refresh_token=refresh_token,
        )

    async def me(self, access_token: str) -> dict:
        async with self._client() as client:
            response = await self._send(
                client, "GET", f"{API_BASE}/me", headers=_bearer(access_token)
            )
        return response.json()

    # ---- プレイリスト作成 ----

    async def build_playlist(
        self, session: Session, name: str, tracks: list[TrackQuery]
    ) -> PlaylistResult:
        """曲を検索し、見つかった曲をチャート順に収めた非公開プレイリストを作る。"""
        lock = asyncio.Lock()
        async with self._client() as client:
            if session.expires_at - REFRESH_MARGIN_SECONDS < self._clock():
                await self._refresh_session(session)

            semaphore = asyncio.Semaphore(SEARCH_CONCURRENCY)

            async def search(track: TrackQuery) -> str | None:
                async with semaphore:
                    return await self._search_track(client, session, lock, track)

            uris = await asyncio.gather(*(search(t) for t in tracks))

            created = await self._authed(
                client,
                session,
                lock,
                "POST",
                f"{API_BASE}/me/playlists",
                json={
                    "name": name,
                    "public": False,
                    "description": "Billboard Hot 100 から作成",
                },
            )
            playlist = created.json()
            playlist_id = playlist["id"]

            found = [uri for uri in uris if uri]
            for start in range(0, len(found), ADD_CHUNK_SIZE):
                await self._authed(
                    client,
                    session,
                    lock,
                    "POST",
                    f"{API_BASE}/playlists/{playlist_id}/items",
                    json={"uris": found[start : start + ADD_CHUNK_SIZE]},
                )

        not_found = [t for t, uri in zip(tracks, uris, strict=True) if not uri]
        logger.info(
            "playlist %s created: %d added, %d not found", playlist_id, len(found), len(not_found)
        )
        return PlaylistResult(
            playlist_id=playlist_id,
            url=playlist.get("external_urls", {}).get("spotify", ""),
            added=len(found),
            not_found=not_found,
        )

    async def _search_track(
        self, client: httpx.AsyncClient, session: Session, lock: asyncio.Lock, track: TrackQuery
    ) -> str | None:
        title = _strip_quotes(track.title)
        artist = _strip_quotes(primary_artist(track.artist))
        queries = [f'track:"{title}" artist:"{artist}"', f"{title} {artist}".strip()]
        for query in queries:
            response = await self._authed(
                client,
                session,
                lock,
                "GET",
                f"{API_BASE}/search",
                params={"q": query, "type": "track", "limit": 1},
            )
            items = response.json().get("tracks", {}).get("items", [])
            if items:
                return items[0]["uri"]
        return None

    # ---- HTTP 共通 ----

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transport, timeout=TIMEOUT_SECONDS)

    async def _token_request(self, form: dict, fallback_refresh_token: str) -> TokenSet:
        async with self._client() as client:
            response = await self._send(
                client,
                "POST",
                TOKEN_URL,
                data=form,
                auth=(self._settings.spotify_client_id, self._settings.spotify_client_secret),
            )
        body = response.json()
        return TokenSet(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token") or fallback_refresh_token,
            expires_at=self._clock() + float(body.get("expires_in", 3600)),
        )

    async def _refresh_session(self, session: Session) -> None:
        tokens = await self.refresh(session.refresh_token)
        session.access_token = tokens.access_token
        session.refresh_token = tokens.refresh_token
        session.expires_at = tokens.expires_at

    async def _authed(
        self,
        client: httpx.AsyncClient,
        session: Session,
        lock: asyncio.Lock,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """セッションのトークンで呼び出し、401 なら1回だけリフレッシュして再試行する。"""
        token = session.access_token
        try:
            return await self._send(client, method, url, headers=_bearer(token), **kwargs)
        except SpotifyError as exc:
            if exc.status != 401:
                raise
        async with lock:
            if session.access_token == token:  # 並行リクエストが既に更新していなければ更新
                await self._refresh_session(session)
        return await self._send(
            client, method, url, headers=_bearer(session.access_token), **kwargs
        )

    async def _send(
        self, client: httpx.AsyncClient, method: str, url: str, **kwargs
    ) -> httpx.Response:
        """429 は Retry-After に従い最大 MAX_RETRIES 回再試行する。2xx 以外は SpotifyError。"""
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                message = f"Spotify に接続できませんでした（{type(exc).__name__}）"
                raise SpotifyError(502, message) from exc
            if response.status_code == 429 and attempt < MAX_RETRIES:
                wait = _retry_after(response)
                logger.warning("Spotify rate limited; retry in %.1fs", wait)
                await self._sleep(wait)
                continue
            if response.is_success:
                return response
            logger.warning("Spotify %s %s -> %s", method, httpx.URL(url).path, response.status_code)
            raise SpotifyError(response.status_code, _error_message(response))
        raise AssertionError("unreachable")  # pragma: no cover


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
