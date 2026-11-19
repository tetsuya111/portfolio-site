"""取得したページから項目を抽出する処理。"""

from urllib.parse import urljoin, urlsplit


def absolute_http_url(href: str | None, base_url: str) -> str:
    """相対リンクを絶対 URL にする。http(s) 以外（javascript: など）は空文字にする。"""
    if not href:
        return ""
    url = urljoin(base_url, href.strip())
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    return url
