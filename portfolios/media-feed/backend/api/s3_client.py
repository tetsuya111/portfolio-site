"""S3クライアントとs3://パスの共通処理。

バケットごとにリージョンが異なりうる（東京への移行期間中は新旧バケットが併存する）ため、
クライアントはリージョン単位でキャッシュし、バケット名から引けるようにする。
"""
import os
import threading

S3_PREFIX = "s3://"

# 既定リージョン。移行後の配信元はこちら。
DEFAULT_REGION = os.environ.get("AWS_REGION") or "ap-northeast-1"

# 配信元バケット（新規アップロード先）
DEFAULT_BUCKET = os.environ.get("MEDIA_S3_BUCKET") or "junk-porn-feed-site"


def _parse_bucket_regions(raw: str) -> dict:
    """"bucket=region,bucket2=region2" 形式を辞書にする。"""
    mapping = {}
    for entry in (raw or "").split(","):
        entry = entry.strip()
        if not entry or "=" not in entry:
            continue
        bucket, _, region = entry.partition("=")
        bucket, region = bucket.strip(), region.strip()
        if bucket and region:
            mapping[bucket] = region
    return mapping


# 既定リージョン以外に存在するバケットの対応表。
# 例: MEDIA_BUCKET_REGIONS="junk-porn-feed-site=ap-southeast-2"
BUCKET_REGIONS = _parse_bucket_regions(os.environ.get("MEDIA_BUCKET_REGIONS", ""))

_clients = {}
_lock = threading.Lock()


def region_for_bucket(bucket: str | None) -> str:
    """バケットが存在するリージョンを返す。未知のバケットは既定リージョン扱い。"""
    if not bucket:
        return DEFAULT_REGION
    return BUCKET_REGIONS.get(bucket, DEFAULT_REGION)


def get_s3_client(bucket: str | None = None, region: str | None = None):
    """リージョン単位でキャッシュしたS3クライアントを返す。

    リージョンが一致しないクライアントで GetObject を呼ぶと SigV4 の署名が合わず
    400 になるため、バケットごとに正しいリージョンのクライアントを使う必要がある。
    """
    resolved = region or region_for_bucket(bucket)
    client = _clients.get(resolved)
    if client is not None:
        return client

    import boto3

    with _lock:
        client = _clients.get(resolved)
        if client is None:
            client = boto3.client(
                "s3",
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                region_name=resolved,
            )
            _clients[resolved] = client
    return client


def is_s3_path(path: str | None) -> bool:
    return bool(path) and path.startswith(S3_PREFIX)


def parse_s3_path(path: str) -> tuple[str, str] | None:
    """s3://bucket/key を (bucket, key) に分解する。形式が違えば None。"""
    if not is_s3_path(path):
        return None
    bucket, _, key = path[len(S3_PREFIX):].partition("/")
    if not bucket or not key:
        return None
    return bucket, key


def build_s3_path(bucket: str, key: str) -> str:
    return f"{S3_PREFIX}{bucket}/{key}"
