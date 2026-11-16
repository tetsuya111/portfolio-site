"""環境変数から設定を読み込む。"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "app.db")
DEFAULT_REDIRECT_URI = "http://127.0.0.1:3000/auth/callback"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:3000"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

logger = logging.getLogger(__name__)


class ConfigError(ValueError):
    """起動を止めるべき設定の誤り。"""


@dataclass(frozen=True)
class Settings:
    spotify_client_id: str
    # repr にシークレットを出さない（ログ・例外メッセージへの漏えい防止）
    spotify_client_secret: str = field(repr=False)
    redirect_uri: str = DEFAULT_REDIRECT_URI
    frontend_url: str = DEFAULT_FRONTEND_URL
    db_path: str = DEFAULT_DB_PATH
    cookie_secure: bool = False
    # 公開時のパスの接頭辞（FRONTEND_URL のパス。例 /apps/<slug>）。Cookie のパスに使う
    public_path: str = ""


def _is_loopback(url: str) -> bool:
    return (urlsplit(url).hostname or "") in LOOPBACK_HOSTS


def _require_https_unless_loopback(name: str, url: str) -> None:
    """https 以外は、ループバックのホストに対する http だけを許す（平文で外部に出さない）。"""
    scheme = urlsplit(url).scheme
    if scheme == "https" or (scheme == "http" and _is_loopback(url)):
        return
    raise ConfigError(f"{name} は https で指定してください（http はループバックのみ可）: {url}")


def _public_path(frontend_url: str) -> str:
    """FRONTEND_URL のパス（末尾の / なし）。バックエンドはフロントエンドと同じパスの下に置く。"""
    parts = urlsplit(frontend_url)
    if parts.query or parts.fragment:
        raise ConfigError(f"FRONTEND_URL にクエリ・フラグメントは付けられません: {frontend_url}")
    return parts.path.rstrip("/")


def _check_redirect_uri(frontend_url: str, public_path: str, redirect_uri: str) -> None:
    """state の Cookie（FRONTEND_URL のホストの <パス>/auth）がコールバックに届くかを確かめる。

    https では Cookie に Secure が付き http のコールバックには届かないため、スキームも揃える。
    """
    frontend, redirect = urlsplit(frontend_url), urlsplit(redirect_uri)
    state_path = public_path + "/auth/"
    if (
        redirect.scheme.lower() != frontend.scheme.lower()
        or redirect.hostname != frontend.hostname
        or not redirect.path.startswith(state_path)
    ):
        raise ConfigError(
            "SPOTIFY_REDIRECT_URI は FRONTEND_URL と同じスキーム・ホストの "
            f"{state_path} の下にしてください（state の Cookie が届かないため）: {redirect_uri}"
        )
    expected = frontend_url + "/auth/callback"
    if redirect_uri != expected:
        # Cookie はポートを区別しないため届くが、想定の構成と違う
        logger.warning(
            "SPOTIFY_REDIRECT_URI (%s) が FRONTEND_URL + /auth/callback (%s) と違います",
            redirect_uri,
            expected,
        )


def _cookie_secure(frontend_url: str) -> bool:
    value = os.environ.get("COOKIE_SECURE", "").strip().lower()
    if value == "":
        return urlsplit(frontend_url).scheme == "https"
    if value == "true":
        return True
    if value == "false":
        # Secure 無しを許すのはループバック（ローカル開発）だけ。公開先で平文に乗せない
        if not _is_loopback(frontend_url):
            raise ConfigError("COOKIE_SECURE=false はループバックの FRONTEND_URL でのみ指定可")
        return False
    raise ConfigError("COOKIE_SECURE は true または false で指定してください")


def load_settings(*, web: bool = True) -> Settings:
    """環境変数から設定を作る。

    web=True（Web アプリの起動）のときは URL と Cookie の設定を検証し、誤りは ConfigError にする。
    バッチのように URL・Cookie を使わない処理は web=False で呼び、検証を省く。
    """
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", DEFAULT_REDIRECT_URI)
    frontend_url = os.environ.get("FRONTEND_URL", DEFAULT_FRONTEND_URL).rstrip("/")
    cookie_secure = False
    public_path = ""
    if web:
        public_path = _public_path(frontend_url)
        _require_https_unless_loopback("FRONTEND_URL", frontend_url)
        _require_https_unless_loopback("SPOTIFY_REDIRECT_URI", redirect_uri)
        cookie_secure = _cookie_secure(frontend_url)
        _check_redirect_uri(frontend_url, public_path, redirect_uri)
    return Settings(
        spotify_client_id=os.environ.get("SPOTIFY_CLIENT_ID", ""),
        spotify_client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", ""),
        redirect_uri=redirect_uri,
        frontend_url=frontend_url,
        db_path=os.environ.get("DB_PATH", DEFAULT_DB_PATH),
        cookie_secure=cookie_secure,
        public_path=public_path,
    )
