"""環境変数から設定を読み込む。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "app.db")
DEFAULT_REDIRECT_URI = "http://127.0.0.1:3000/auth/callback"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:3000"


@dataclass(frozen=True)
class Settings:
    spotify_client_id: str
    # repr にシークレットを出さない（ログ・例外メッセージへの漏えい防止）
    spotify_client_secret: str = field(repr=False)
    redirect_uri: str = DEFAULT_REDIRECT_URI
    frontend_url: str = DEFAULT_FRONTEND_URL
    db_path: str = DEFAULT_DB_PATH


def load_settings() -> Settings:
    return Settings(
        spotify_client_id=os.environ.get("SPOTIFY_CLIENT_ID", ""),
        spotify_client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", ""),
        redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", DEFAULT_REDIRECT_URI),
        frontend_url=os.environ.get("FRONTEND_URL", DEFAULT_FRONTEND_URL).rstrip("/"),
        db_path=os.environ.get("DB_PATH", DEFAULT_DB_PATH),
    )
