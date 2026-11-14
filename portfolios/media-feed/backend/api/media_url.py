"""配信URLの解決。

メディア本体をアプリケーションサーバに通さないための入口。
一覧APIのレスポンスにURLを同梱することで、URL取得のための往復を増やさずに
ブラウザが直接エッジ（またはS3）から取得できるようにする。

署名URLの有効期限は1時間境界に量子化する。リクエストごとにURLが変わると
ブラウザキャッシュのキーが毎回変わり、再視聴で必ず再取得になるため。
"""
import logging
import os
import time
from functools import lru_cache

from django.conf import settings

from .s3_client import get_s3_client, parse_s3_path

logger = logging.getLogger(__name__)

MODE_CDN = "cdn"      # CloudFront 署名付きURL
MODE_S3 = "s3"        # S3 presigned URL（CDN未整備でもアプリを経路から外せる）
MODE_PROXY = "proxy"  # 従来のアプリ中継（ローカル開発・フォールバック）

# 署名URLを配る間隔。この単位でURLが変わる。
_QUANTUM = 3600


def delivery_mode() -> str:
    mode = (os.environ.get("MEDIA_DELIVERY_MODE") or MODE_PROXY).strip().lower()
    return mode if mode in (MODE_CDN, MODE_S3, MODE_PROXY) else MODE_PROXY


def signed_url_ttl() -> int:
    try:
        return int(os.environ.get("MEDIA_SIGNED_URL_TTL", 6 * 3600))
    except ValueError:
        return 6 * 3600


def _expiry_window(now: float | None = None) -> int:
    """現在時刻を含む量子化窓の識別子。同じ窓の間は同じURLを返す。"""
    return int((now if now is not None else time.time()) // _QUANTUM)


def quantized_expires_at(now: float | None = None) -> int:
    """次の時間境界 + TTL。窓が変わるまで同じ値を返す。"""
    return (_expiry_window(now) + 1) * _QUANTUM + signed_url_ttl()


def resolve_media_url(content) -> str | None:
    """Content の配信URLを返す。

    None を返した場合、呼び出し側（フロント）は従来のアプリ経由URLを使う。
    I/O は行わない。署名は純粋な計算で、S3 へは問い合わせない。
    """
    path = (content.path or "").strip()
    if not path:
        return None

    # 既に絶対URLならそのまま。
    if path.startswith("http://") or path.startswith("https://"):
        return path

    parsed = parse_s3_path(path)
    if not parsed:
        # ローカルファイル。アプリ経由でしか返せない。
        return None

    bucket, key = parsed
    mode = delivery_mode()

    if mode == MODE_CDN:
        url = _cloudfront_signed_url(key)
        if url:
            return url
        # 鍵が未設定・署名失敗ならアプリ経由に退避する。
        return None

    if mode == MODE_S3:
        return _s3_presigned_url(bucket, key)

    return None


def _cloudfront_domain() -> str:
    return (os.environ.get("CLOUDFRONT_DOMAIN") or "").strip().rstrip("/")


def _cloudfront_signed_url(key: str) -> str | None:
    domain = _cloudfront_domain()
    key_pair_id = (os.environ.get("CLOUDFRONT_KEY_PAIR_ID") or "").strip()
    private_key_path = (os.environ.get("CLOUDFRONT_PRIVATE_KEY_PATH") or "").strip()
    if not (domain and key_pair_id and private_key_path):
        return None

    try:
        signer = _cloudfront_signer(key_pair_id, private_key_path)
        if signer is None:
            return None
        from datetime import datetime, timezone

        base = domain if "://" in domain else f"https://{domain}"
        url = f"{base}/{key.lstrip('/')}"
        expires = datetime.fromtimestamp(quantized_expires_at(), tz=timezone.utc)
        return signer.generate_presigned_url(url, date_less_than=expires)
    except Exception:
        logger.exception("CloudFront の署名に失敗しました。アプリ経由に退避します。")
        return None


@lru_cache(maxsize=1)
def _cloudfront_signer(key_pair_id: str, private_key_path: str):
    """署名器は使い回す。鍵の読み込みとパースを毎回やらないため。"""
    try:
        from botocore.signers import CloudFrontSigner
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError:
        logger.warning(
            "cryptography が未インストールのため CloudFront 署名を利用できません。"
        )
        return None

    with open(private_key_path, "rb") as fh:
        private_key = serialization.load_pem_private_key(
            fh.read(), password=None, backend=default_backend()
        )

    def rsa_signer(message: bytes) -> bytes:
        return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())

    return CloudFrontSigner(key_pair_id, rsa_signer)


def _s3_presigned_url(bucket: str, key: str) -> str | None:
    # 署名にはリクエスト時刻が埋め込まれるため、窓ごとにキャッシュしてURLを固定する。
    return _s3_presigned_url_cached(bucket, key, _expiry_window())


@lru_cache(maxsize=4096)
def _s3_presigned_url_cached(bucket: str, key: str, window: int) -> str | None:
    try:
        s3 = get_s3_client(bucket=bucket)
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=signed_url_ttl() + _QUANTUM,
        )
    except Exception:
        logger.exception("S3 presigned URL の生成に失敗しました。アプリ経由に退避します。")
        return None


def resolve_poster_url(content) -> str | None:
    """動画のサムネイルURL。

    正規化バッチ（tasks.md のタスク16）がサムネイルを生成するまでは常に None。
    一覧20件で存在確認のI/Oを出さないため、S3 への問い合わせは行わない。
    """
    if getattr(content, "type", None) != "video":
        return None
    if getattr(content, "media_version", 0) < 1:
        return None

    parsed = parse_s3_path(content.path or "")
    if not parsed:
        return None
    bucket, _ = parsed
    key = f"media/thumbs/{content.id}.jpg"

    mode = delivery_mode()
    if mode == MODE_CDN:
        return _cloudfront_signed_url(key)
    if mode == MODE_S3:
        return _s3_presigned_url(bucket, key)
    return None
