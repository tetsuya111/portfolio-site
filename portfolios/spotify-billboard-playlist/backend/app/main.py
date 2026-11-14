"""FastAPI アプリケーション。

起動: `uvicorn app.main:create_default_app --factory --env-file .env --port 8000`
"""

import logging
import secrets
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.batch.fetcher import Fetcher, FetchError
from app.batch.parser import ParseError
from app.batch.runner import PageFetcher, process_chart_page
from app.batch.urls import MAX_URL_LENGTH, InvalidChartUrl
from app.config import Settings, load_settings
from app.db import Database
from app.ratelimit import CHART_RATE_LIMIT, CHART_RATE_WINDOW, RateLimiter
from app.sessions import SESSION_MAX_AGE, Session, SessionStore
from app.spotify import SpotifyClient, SpotifyError, TrackQuery

logger = logging.getLogger(__name__)

STATE_COOKIE = "oauth_state"
SESSION_COOKIE = "sid"
STATE_MAX_AGE = 600
CSRF_HEADER = "X-CSRF-Token"


class ChartRequest(BaseModel):
    url: str = Field(min_length=1, max_length=MAX_URL_LENGTH)


class Track(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    artist: str = Field(default="", max_length=200)


class ChartTrack(Track):
    rank: int


class ChartResponse(BaseModel):
    id: int
    url: str
    title: str  # ページの <title>（サイト名を除く。無ければ空文字）。プレイリスト名に使う
    tracks: list[ChartTrack]


class PlaylistRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    tracks: list[Track] = Field(min_length=1, max_length=100)


class PlaylistResponse(BaseModel):
    playlist_id: str
    url: str
    added: int
    not_found: list[Track]


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def create_app(
    settings: Settings,
    db: Database,
    fetcher: PageFetcher,
    spotify: SpotifyClient,
    sessions: SessionStore,
    chart_limiter: RateLimiter | None = None,
) -> FastAPI:
    app = FastAPI(title="Billboard → Spotify Playlist")
    secure_cookie = settings.cookie_secure
    limiter = chart_limiter or RateLimiter(CHART_RATE_LIMIT, CHART_RATE_WINDOW)

    def require_same_origin(request: Request) -> None:
        """状態を変更するリクエストはフロントエンドのオリジンからのみ受け付ける（CSRF対策）。

        Origin が無いときは Sec-Fetch-Site: same-origin の場合だけ許し、どちらも無ければ拒否する。
        """
        origin = request.headers.get("origin")
        if origin is not None:
            allowed = origin == _origin(settings.frontend_url)
        else:
            allowed = request.headers.get("sec-fetch-site") == "same-origin"
        if not allowed:
            raise HTTPException(status_code=403, detail="許可されていないオリジンです")

    def current_session(
        sid: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    ) -> tuple[str, Session] | None:
        session = sessions.get(sid or "")
        return (sid, session) if sid and session else None

    CurrentSession = Annotated[tuple[str, Session] | None, Depends(current_session)]

    def require_csrf(request: Request, current: CurrentSession) -> None:
        """ログイン中のセッションでは、セッションに紐付く CSRF トークンをヘッダーで要求する。"""
        if current is None:
            return
        token = request.headers.get(CSRF_HEADER, "")
        if not secrets.compare_digest(token.encode(), current[1].csrf_token.encode()):
            logger.warning("CSRF token mismatch for %s", request.url.path)
            raise HTTPException(status_code=403, detail="不正なリクエストです（CSRFトークン）")

    # same_origin → セッション → CSRF の順に判定する
    protected = [Depends(require_same_origin), Depends(require_csrf)]

    # ---- チャート ----

    @app.post("/api/charts", response_model=ChartResponse, dependencies=protected)
    def post_chart(body: ChartRequest, current: CurrentSession) -> ChartResponse:
        if current is None:
            raise HTTPException(status_code=401, detail="Spotify にログインしてください")
        if not limiter.allow(current[1].user_id):
            logger.warning("chart rate limit exceeded")
            detail = "リクエストが多すぎます。しばらく待ってから再度お試しください"
            raise HTTPException(status_code=429, detail=detail)
        source_id = db.add_source(body.url.strip())
        try:
            page = process_chart_page(db, source_id, fetcher)
        except InvalidChartUrl as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (FetchError, ParseError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return ChartResponse(
            id=source_id,
            url=body.url.strip(),
            title=page.title,
            tracks=[ChartTrack(rank=e.rank, title=e.title, artist=e.artist) for e in page.entries],
        )

    # ---- 認証 ----

    @app.get("/auth/login")
    def login() -> RedirectResponse:
        if not settings.spotify_client_id or not settings.spotify_client_secret:
            raise HTTPException(
                status_code=500, detail="Spotify のクライアント設定（.env）がありません"
            )
        state = secrets.token_urlsafe(32)
        response = RedirectResponse(spotify.authorize_url(state), status_code=302)
        response.set_cookie(
            STATE_COOKIE,
            state,
            max_age=STATE_MAX_AGE,
            path="/auth",
            httponly=True,
            samesite="lax",
            secure=secure_cookie,
        )
        return response

    @app.get("/auth/callback")
    async def callback(
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
        oauth_state: Annotated[str | None, Cookie(alias=STATE_COOKIE)] = None,
    ) -> RedirectResponse:
        if not state or not oauth_state or not secrets.compare_digest(state, oauth_state):
            raise HTTPException(status_code=400, detail="認可リクエストの state が一致しません")
        if error or not code:
            raise HTTPException(status_code=400, detail="Spotify での認可が完了しませんでした")
        try:
            tokens = await spotify.exchange_code(code)
            profile = await spotify.me(tokens.access_token)
        except SpotifyError as exc:
            logger.warning("OAuth callback failed: %s", exc.status)
            detail = "Spotify へのログインに失敗しました"
            raise HTTPException(status_code=400, detail=detail) from exc
        sid = sessions.create(
            Session(
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                expires_at=tokens.expires_at,
                user_id=str(profile.get("id", "")),
                display_name=str(profile.get("display_name") or profile.get("id", "")),
            )
        )
        response = RedirectResponse(settings.frontend_url + "/", status_code=302)
        response.delete_cookie(STATE_COOKIE, path="/auth")
        response.set_cookie(
            SESSION_COOKIE,
            sid,
            max_age=SESSION_MAX_AGE,
            path="/",
            httponly=True,
            samesite="lax",
            secure=secure_cookie,
        )
        return response

    @app.get("/api/me")
    def me(current: CurrentSession) -> dict:
        if current is None:
            return {"authenticated": False}
        _, session = current
        return {
            "authenticated": True,
            "id": session.user_id,
            "display_name": session.display_name,
            # 同一オリジンの画面だけが読める（CORS 未設定）。状態を変える POST に付けて送り返す
            "csrf_token": session.csrf_token,
        }

    @app.post("/auth/logout", status_code=204, dependencies=protected)
    def logout(current: CurrentSession) -> Response:
        if current is not None:
            sessions.delete(current[0])
        response = Response(status_code=204)
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    # ---- プレイリスト ----

    @app.post(
        "/api/playlists",
        status_code=201,
        response_model=PlaylistResponse,
        dependencies=protected,
    )
    async def create_playlist(body: PlaylistRequest, current: CurrentSession) -> PlaylistResponse:
        if current is None:
            raise HTTPException(status_code=401, detail="Spotify にログインしてください")
        sid, session = current
        try:
            result = await spotify.build_playlist(
                session, body.name, [TrackQuery(t.title, t.artist) for t in body.tracks]
            )
        except SpotifyError as exc:
            if exc.status == 401:
                sessions.delete(sid)
                raise HTTPException(
                    status_code=401, detail="ログインの有効期限が切れました。再ログインしてください"
                ) from exc
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return PlaylistResponse(
            playlist_id=result.playlist_id,
            url=result.url,
            added=result.added,
            not_found=[Track(title=t.title, artist=t.artist) for t in result.not_found],
        )

    return app


def create_default_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    return create_app(
        settings, Database(settings.db_path), Fetcher(), SpotifyClient(settings), SessionStore()
    )
