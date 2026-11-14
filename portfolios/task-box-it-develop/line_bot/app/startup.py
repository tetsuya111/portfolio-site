"""起動時の設定。

公開URLを決め、`USE_NGROK=true` のときだけ LINE のWebhookエンドポイントを合わせる。
開発の利便性のための処理なので、**どこで失敗しても例外を外に出さず、起動を止めない**。
`USE_NGROK=false`（既定・本番）ではLINEのAPIを一切呼ばない（本番の設定を上書きしないため）。
"""

import logging
import unicodedata

from . import public_url
from .config import get_settings
from .line.client import LineApiError, get_client

logger = logging.getLogger(__name__)

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def setup_logging() -> None:
    """uvicorn配下ではアプリのロガーにハンドラが付かず、INFOのログが出ない。ここで用意する。"""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    elif root.level > logging.INFO:
        root.setLevel(logging.INFO)


def _width(text: str) -> int:
    """端末での表示幅。日本語は2文字分として数える。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def show_links() -> None:
    """起動時に、開発で使うリンクをまとめて出す。"""
    settings = get_settings()
    url = public_url.current()
    lines = [("公開URL", url or "(未設定)")]
    if url:
        lines.append(("Webhook URL", public_url.webhook_url()))
        if settings.liff_id:
            lines.append(("LIFFのエンドポイント", public_url.liff_endpoint_url()))
    if settings.use_ngrok:
        lines.append(("ngrokの管理画面", public_url.ngrok_inspector_url()))
    width = max(_width(label) for label, _ in lines)
    logger.info("-" * 60)
    for label, value in lines:
        logger.info("%s : %s", label + " " * (width - _width(label)), value)
    logger.info("-" * 60)


def configure_public_url() -> None:
    """起動時の設定。開発の利便性のための処理なので、何があっても起動を止めない。"""
    try:
        _configure_public_url()
    except Exception as exc:  # 想定外の失敗でアプリが起動できなくなるのを防ぐ
        logger.warning("公開URLの設定に失敗しました（起動は続けます）: %r", exc)


def _configure_public_url() -> None:
    settings = get_settings()
    url = public_url.resolve()

    if not settings.use_ngrok:
        show_links()
        return

    logger.info("ngrokの公開URLを使用します")
    show_links()
    if settings.environment == "production":
        logger.warning(
            "ENVIRONMENT=production ですが USE_NGROK が有効です。本番では無効にしてください"
        )
    if not url:
        logger.warning(
            "公開URLが取得できないため、LINEのWebhookエンドポイントは更新しません"
            "（先に `ngrok http 8100` を起動してください）"
        )
        return

    if not settings.channel_access_token:
        logger.warning(
            "LINE_CHANNEL_ACCESS_TOKEN が未設定のため、Webhookエンドポイントを更新できません。"
            "LINE Developers で次のURLを設定してください: %s", public_url.webhook_url(),
        )
        return

    _update_webhook_endpoint(public_url.webhook_url())
    if settings.liff_id:
        # LIFFアプリのエンドポイントは自動更新しない（design.md「LIFFの扱い」）
        logger.info(
            "LIFFアプリのエンドポイントには、上の「LIFFのエンドポイント」のURLを設定してください"
        )


def _update_webhook_endpoint(url: str) -> None:
    client = get_client()
    try:
        configured = client.get_webhook_endpoint()
    except LineApiError as exc:
        logger.warning("現在のWebhookエンドポイントを取得できません: %s", exc)
        configured = None

    if configured == url:
        logger.info("LINEのWebhookエンドポイントは最新です: %s", url)
        return

    try:
        client.set_webhook_endpoint(url)
    except LineApiError as exc:
        logger.warning(
            "LINEのWebhookエンドポイントを更新できませんでした（%s）。"
            "LINE Developers で次のURLを設定してください: %s", exc, url,
        )
        return
    logger.info("LINEのWebhookエンドポイントを設定しました: %s", url)

    try:
        ok = client.test_webhook_endpoint()
    except LineApiError as exc:
        logger.warning("Webhookの疎通確認に失敗しました: %s", exc)
        return
    if ok:
        logger.info("Webhookの疎通確認に成功しました")
    else:
        logger.warning("Webhookの疎通確認に失敗しました（LINEから応答を得られていません）")
