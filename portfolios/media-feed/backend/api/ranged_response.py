"""メディア配信用の HTTP Range / 条件付きGET レスポンス。

Django 6.0 の FileResponse は Range を解釈しないため、ここで自前に実装する。
`<video>` のシークは Range の上に成り立っており、これが無いと
「先頭から全部ダウンロードし直す」以外の再生手段が無くなる。

S3経路では Range と条件付きGETの判定を S3 に委譲する。手元でサイズを調べてから
本体を取りに行くと往復が2回になるため、判定ごと1回のリクエストに畳んでいる。
"""
import mimetypes
import re

from django.http import HttpResponse, StreamingHttpResponse
from django.utils.http import http_date, parse_http_date_safe

# 8KBでは1本の動画で数万回のwriteが発生し、syscallのオーバーヘッドが支配的になる。
CHUNK_SIZE = 256 * 1024

_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


class RangeNotSatisfiable(Exception):
    """構文は妥当だが、対象ファイルに対して範囲が成立しない (416)。"""


def parse_range_header(header: str | None, total: int) -> tuple[int, int] | None:
    """Range ヘッダを (start, end) の閉区間に解釈する。

    戻り値:
        None                 -- Rangeなし、または構文が不正。全体を返す (200)。
        (start, end)         -- 部分応答 (206)。
    例外:
        RangeNotSatisfiable  -- 構文は妥当だが範囲が成立しない (416)。

    RFC 9110 に従い、構文が不正な Range ヘッダは「無視して200」とする。
    416 を返すのは、構文が妥当でかつ範囲が成立しない場合だけ。
    """
    if not header:
        return None

    header = header.strip()
    # 複数範囲 (bytes=0-99,200-299) は先頭だけを扱う。動画再生では単一範囲しか使われない。
    if "," in header:
        header = header.split(",", 1)[0].strip()
        if not header.startswith("bytes="):
            header = "bytes=" + header

    m = _RANGE_RE.match(header)
    if not m:
        return None  # 単位が bytes でない等。無視して200。

    first, last = m.group(1), m.group(2)

    if first == "" and last == "":
        return None  # "bytes=-" は不正。

    if first == "":
        # 末尾 N バイト。
        suffix = int(last)
        if suffix == 0:
            raise RangeNotSatisfiable
        if total == 0:
            raise RangeNotSatisfiable
        start = max(0, total - suffix)
        return start, total - 1

    start = int(first)
    if last == "":
        end = total - 1
    else:
        end = int(last)
        if end < start:
            return None  # 逆転は不正な構文として無視する。
        end = min(end, total - 1)

    if total == 0 or start >= total:
        raise RangeNotSatisfiable

    return start, end


def make_etag(size: int, mtime: float) -> str:
    """ローカルファイル用の弱くない ETag。内容が変われば size か mtime が変わる。"""
    return f'"{int(mtime):x}-{size:x}"'


def is_not_modified(request, etag: str | None, last_modified: float | None) -> bool:
    """条件付きGETに対して 304 を返してよいかを判定する。

    ConditionalGetMiddleware は Range と併用すると 206 を壊すため、ここで明示的に見る。
    RFC 9110 に従い If-None-Match を If-Modified-Since より優先する。
    """
    if_none_match = request.META.get("HTTP_IF_NONE_MATCH")
    if if_none_match and etag:
        candidates = [t.strip() for t in if_none_match.split(",")]
        if "*" in candidates:
            return True
        # 弱い比較: W/ 接頭辞を落として比べる。
        normalized = etag[2:] if etag.startswith("W/") else etag
        for tag in candidates:
            if (tag[2:] if tag.startswith("W/") else tag) == normalized:
                return True
        return False

    if_modified_since = request.META.get("HTTP_IF_MODIFIED_SINCE")
    if if_modified_since and last_modified is not None:
        since = parse_http_date_safe(if_modified_since)
        if since is not None and int(last_modified) <= since:
            return True

    return False


def _apply_common_headers(response, *, etag, last_modified, cache_max_age):
    response["Accept-Ranges"] = "bytes"
    if etag:
        response["ETag"] = etag
    if last_modified is not None:
        response["Last-Modified"] = http_date(last_modified)
    if cache_max_age:
        # コンテンツIDが内容のハッシュに紐づくため、内容が変わればURLも変わる。
        response["Cache-Control"] = f"public, max-age={cache_max_age}, immutable"
    return response


def not_modified_response(*, etag=None, last_modified=None, cache_max_age=None):
    response = HttpResponse(status=304)
    return _apply_common_headers(
        response, etag=etag, last_modified=last_modified, cache_max_age=cache_max_age
    )


def range_not_satisfiable_response(total: int):
    response = HttpResponse(status=416)
    response["Content-Range"] = f"bytes */{total}"
    response["Accept-Ranges"] = "bytes"
    return response


def _file_iterator(fh, length: int, chunk_size: int = CHUNK_SIZE):
    """開始位置までseek済みのファイルから、length バイトだけ読み出す。"""
    remaining = length
    try:
        while remaining > 0:
            chunk = fh.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:
        fh.close()


def local_file_response(request, filepath, *, cache_max_age=None):
    """ローカルファイルを Range 対応で返す。"""
    stat = filepath.stat()
    total = stat.st_size
    etag = make_etag(total, stat.st_mtime)

    if is_not_modified(request, etag, stat.st_mtime):
        return not_modified_response(
            etag=etag, last_modified=stat.st_mtime, cache_max_age=cache_max_age
        )

    try:
        rng = parse_range_header(request.META.get("HTTP_RANGE"), total)
    except RangeNotSatisfiable:
        return range_not_satisfiable_response(total)

    content_type = mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"
    fh = open(filepath, "rb")

    if rng is None:
        response = StreamingHttpResponse(
            _file_iterator(fh, total), content_type=content_type
        )
        response["Content-Length"] = str(total)
    else:
        start, end = rng
        length = end - start + 1
        fh.seek(start)
        response = StreamingHttpResponse(
            _file_iterator(fh, length), content_type=content_type, status=206
        )
        response["Content-Length"] = str(length)
        response["Content-Range"] = f"bytes {start}-{end}/{total}"

    return _apply_common_headers(
        response, etag=etag, last_modified=stat.st_mtime, cache_max_age=cache_max_age
    )


def s3_object_response(request, s3, bucket: str, key: str, *, cache_max_age=None):
    """S3オブジェクトを Range 対応で返す。

    Range と条件付きGETの判定を S3 に委ねることで、サイズ確認の往復を省いている。
    戻り値が None の場合は対象が存在しない (404)。
    """
    kwargs = {"Bucket": bucket, "Key": key}

    range_header = (request.META.get("HTTP_RANGE") or "").strip()
    # 構文が不正なものは送らない。S3に解釈させる前に弾いて、意図せぬ416を避ける。
    if range_header.startswith("bytes=") and _RANGE_RE.match(range_header.split(",", 1)[0]):
        kwargs["Range"] = range_header

    if_none_match = request.META.get("HTTP_IF_NONE_MATCH")
    if if_none_match:
        kwargs["IfNoneMatch"] = if_none_match

    if_modified_since = request.META.get("HTTP_IF_MODIFIED_SINCE")
    if if_modified_since and not if_none_match:
        since = parse_http_date_safe(if_modified_since)
        if since is not None:
            from datetime import datetime, timezone

            kwargs["IfModifiedSince"] = datetime.fromtimestamp(since, tz=timezone.utc)

    try:
        obj = s3.get_object(**kwargs)
    except Exception as e:
        code = _error_code(e)
        if code in ("304", "NotModified"):
            return not_modified_response(cache_max_age=cache_max_age)
        if code in ("InvalidRange", "RequestedRangeNotSatisfiable"):
            total = _object_size(s3, bucket, key)
            return range_not_satisfiable_response(total)
        if code in ("NoSuchKey", "404", "NoSuchBucket"):
            return None
        raise

    content_type = (
        obj.get("ContentType")
        or mimetypes.guess_type(key)[0]
        or "application/octet-stream"
    )
    content_range = obj.get("ContentRange")

    response = StreamingHttpResponse(
        obj["Body"].iter_chunks(chunk_size=CHUNK_SIZE),
        content_type=content_type,
        status=206 if content_range else 200,
    )
    response["Content-Length"] = str(obj["ContentLength"])
    if content_range:
        response["Content-Range"] = content_range

    last_modified = obj.get("LastModified")
    return _apply_common_headers(
        response,
        etag=obj.get("ETag"),
        last_modified=last_modified.timestamp() if last_modified else None,
        cache_max_age=cache_max_age,
    )


def _error_code(exc) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error") or {}
        code = error.get("Code")
        if code:
            return str(code)
        status_code = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
        if status_code:
            return str(status_code)
    return exc.__class__.__name__


def _object_size(s3, bucket: str, key: str) -> int:
    try:
        return s3.head_object(Bucket=bucket, Key=key).get("ContentLength", 0)
    except Exception:
        return 0
