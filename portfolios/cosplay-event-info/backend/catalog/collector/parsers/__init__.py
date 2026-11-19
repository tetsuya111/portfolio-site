"""取得したページから項目を抽出する処理。"""

from urllib.parse import urljoin, urlsplit


def is_http_url(url: str | None) -> bool:
    """http(s) の絶対 URL かどうか（javascript: や data: を通さない。NF-5）。"""
    parts = urlsplit(url or "")
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def absolute_http_url(href: str | None, base_url: str) -> str:
    """相対リンクを絶対 URL にする。http(s) 以外は空文字にする。"""
    if not href:
        return ""
    url = urljoin(base_url, href.strip())
    return url if is_http_url(url) else ""
