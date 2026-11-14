"""環境変数から設定を読み込む。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "app.db")
DEFAULT_REDIRECT_URI = "http://127.0.0.1:3000/auth/callback"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:3000"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


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


def _require_https_unless_loopback(name: str, url: str) -> None:
    """https 以外は、ループバックのホストに対する http だけを許す（平文で外部に出さない）。"""
    parts = urlsplit(url)
    if parts.scheme == "https":
        return
    if parts.scheme == "http" and (parts.hostname or "") in LOOPBACK_HOSTS:
        return
    raise ConfigError(f"{name} は https で指定してください（http はループバックのみ可）: {url}")


def _cookie_secure(frontend_url: str) -> bool:
    parts = urlsplit(frontend_url)
    value = os.environ.get("COOKIE_SECURE", "").strip().lower()
    if value == "":
        return parts.scheme == "https"
    if value == "true":
        return True
    if value == "false":
        # Secure 無しを許すのはループバック（ローカル開発）だけ。公開先で平文に乗せない
        if (parts.hostname or "") not in LOOPBACK_HOSTS:
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
    if web:
        _require_https_unless_loopback("FRONTEND_URL", frontend_url)
        _require_https_unless_loopback("SPOTIFY_REDIRECT_URI", redirect_uri)
        cookie_secure = _cookie_secure(frontend_url)
    return Settings(
        spotify_client_id=os.environ.get("SPOTIFY_CLIENT_ID", ""),
        spotify_client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", ""),
        redirect_uri=redirect_uri,
        frontend_url=frontend_url,
        db_path=os.environ.get("DB_PATH", DEFAULT_DB_PATH),
        cookie_secure=cookie_secure,
    )
