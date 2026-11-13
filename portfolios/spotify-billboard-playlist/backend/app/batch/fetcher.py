"""チャートページのHTTP取得。取得先ホスト・スキーム・サイズを制限する。"""

from __future__ import annotations

from urllib.parse import urlsplit

import httpx

from app.batch.urls import HOST

TIMEOUT_SECONDS = 10.0
MAX_BYTES = 2 * 1024 * 1024
USER_AGENT = "spotify-billboard-playlist/0.1 (+local portfolio app)"


class FetchError(RuntimeError):
    """ページを取得できなかった。"""


class Fetcher:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def get(self, url: str) -> str:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname != HOST or parts.port is not None:
            raise FetchError(f"取得できるのは https://{HOST}/ のページのみです")
        try:
            with (
                httpx.Client(
                    transport=self._transport,
                    timeout=TIMEOUT_SECONDS,
                    follow_redirects=False,
                    headers={"User-Agent": USER_AGENT},
                ) as client,
                client.stream("GET", url) as response,
            ):
                if response.status_code != 200:
                    raise FetchError(
                        f"チャートページの取得に失敗しました（HTTP {response.status_code}）"
                    )
                chunks = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise FetchError("チャートページが大きすぎます")
                    chunks.append(chunk)
                encoding = response.encoding or "utf-8"
        except httpx.HTTPError as exc:
            raise FetchError(f"チャートページの取得に失敗しました（{type(exc).__name__}）") from exc
        return b"".join(chunks).decode(encoding, errors="replace")
