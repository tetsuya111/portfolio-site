"""公開URL（インターネットからこのアプリに届くURL）の決定。

決める場所をここ1か所にし、Webhookの設定・LIFFの案内・ログ・`/healthz` はすべてこの値を使う。
解決は起動時の1回だけで、リクエストの処理経路では行わない。

`USE_NGROK=true` のときは、**別途起動されているngrok**のローカルAPIから公開URLを読む
（アプリはトンネルを張らない。張るとリロードのたびにURLが変わるため）。
"""

import logging

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/webhook"
LIFF_PATH = "/liff"
NGROK_TIMEOUT = 3.0

_current = ""


def normalize(url: str) -> str:
    """末尾のスラッシュと前後の空白を落とす。"""
    return (url or "").strip().rstrip("/")


def from_ngrok() -> str:
    """ngrokのローカルAPIから https のトンネルのURLを返す。取れなければ空文字。"""
    settings = get_settings()
    try:
        response = httpx.get(settings.ngrok_api_url, timeout=NGROK_TIMEOUT)
        response.raise_for_status()
        tunnels = response.json().get("tunnels") or []
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        logger.warning(
            "ngrokの公開URLを取得できません（ngrokが起動していない可能性）: %s", type(exc).__name__
        )
        return ""
    for tunnel in tunnels:
        name = settings.ngrok_tunnel_name
        if name and tunnel.get("name") != name:
            continue
        url = normalize(tunnel.get("public_url", ""))
        if url.startswith("https://"):
            return url
    logger.warning("ngrokにhttpsのトンネルが見つかりません（トンネル %d件）", len(tunnels))
    return ""


def resolve() -> str:
    """公開URLを決めて保持する。起動時に1回だけ呼ぶ。"""
    global _current
    settings = get_settings()
    url = normalize(settings.public_base_url)
    if settings.use_ngrok:
        url = from_ngrok() or url
    if url and not url.startswith("https://"):
        # LINEのWebhookはHTTPSのみ。値は捨てず、気づけるように警告だけ出す
        logger.warning("公開URLがHTTPSではありません: %s", url)
    _current = url
    return url


def current() -> str:
    return _current


def ngrok_inspector_url() -> str:
    """ngrokの管理画面（送受信の中身を確認できる）。"""
    api = get_settings().ngrok_api_url
    return api.split("/api/")[0] if "/api/" in api else api


def set_current(url: str) -> None:
    """テストや手動での上書き用。"""
    global _current
    _current = normalize(url)


def webhook_url() -> str:
    return f"{_current}{WEBHOOK_PATH}" if _current else ""


def liff_endpoint_url() -> str:
    return f"{_current}{LIFF_PATH}" if _current else ""
