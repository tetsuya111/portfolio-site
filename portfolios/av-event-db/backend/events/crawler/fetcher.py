"""対象サイトのページ取得。robots.txt・アクセス間隔・取得ページのログを扱う。

対応要件: REQ-1.4〜1.6, REQ-2
"""

from __future__ import annotations

import enum
import hashlib
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from django.conf import settings

from events.models import FetchedPage

USER_AGENT = "av-event-db-crawler/0.1"
TIMEOUT_SECONDS = 10.0
_META_CHARSET = re.compile(rb"""<meta[^>]+charset=["']?([\w-]+)""", re.IGNORECASE)


class FetchStatus(enum.Enum):
    FETCHED = "fetched"
    SKIPPED = "skipped"  # 取得済みの詳細ページ
    FAILED = "failed"
    DISALLOWED = "disallowed"


@dataclass(frozen=True)
class FetchResult:
    status: FetchStatus
    body: str = ""


def _decode(response: httpx.Response) -> str:
    if response.charset_encoding:
        return response.text
    m = _META_CHARSET.search(response.content[:4096])
    if m:
        try:
            return response.content.decode(m.group(1).decode("ascii"), errors="replace")
        except LookupError:
            pass
    return response.content.decode("utf-8", errors="replace")


class PageFetcher:
    def __init__(
        self,
        client: httpx.Client | None = None,
        min_interval: float | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)
        self._min_interval = settings.FETCH_MIN_INTERVAL if min_interval is None else min_interval
        self._sleep = sleep
        self._clock = clock
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}

    def close(self) -> None:
        self._client.close()

    def fetch(
        self, url: str, source_name: str, kind: str, cookies: dict[str, str] | None = None
    ) -> FetchResult:
        if (
            kind == FetchedPage.Kind.DETAIL
            and FetchedPage.objects.filter(url=url, result=FetchedPage.Result.SUCCESS).exists()
        ):
            return FetchResult(FetchStatus.SKIPPED)

        if not self._allowed(url):
            self._record(url, source_name, kind, result=FetchedPage.Result.DISALLOWED)
            return FetchResult(FetchStatus.DISALLOWED)

        try:
            response = self._get(url, cookies)
        except httpx.HTTPError as exc:
            self._record(url, source_name, kind, result=FetchedPage.Result.FAILED, error=str(exc))
            return FetchResult(FetchStatus.FAILED)

        if response.status_code >= 400:
            self._record(
                url,
                source_name,
                kind,
                result=FetchedPage.Result.FAILED,
                status_code=response.status_code,
                error=f"HTTP {response.status_code}",
            )
            return FetchResult(FetchStatus.FAILED)

        body = _decode(response)
        self._record(
            url,
            source_name,
            kind,
            result=FetchedPage.Result.SUCCESS,
            status_code=response.status_code,
            body=body,
        )
        return FetchResult(FetchStatus.FETCHED, body)

    def mark_failed(self, url: str, error: str) -> None:
        """取得は成功したが解析できなかったページを失敗扱いにし、次回再取得させる。"""
        FetchedPage.objects.filter(url=url).update(result=FetchedPage.Result.FAILED, error=error)

    def _get(self, url: str, cookies: dict[str, str] | None) -> httpx.Response:
        host = urlsplit(url).netloc
        last = self._last_request.get(host)
        if last is not None:
            wait = self._min_interval - (self._clock() - last)
            if wait > 0:
                self._sleep(wait)
        headers = {"User-Agent": USER_AGENT}
        if cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
        try:
            return self._client.get(
                url, headers=headers, follow_redirects=True, timeout=TIMEOUT_SECONDS
            )
        finally:
            self._last_request[host] = self._clock()

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = self._load_robots(origin)
        parser = self._robots[origin]
        return parser is None or parser.can_fetch(USER_AGENT, url)

    def _load_robots(self, origin: str) -> RobotFileParser | None:
        """robots.txt を読む。取得できなければ制限なし（None）とみなす。"""
        try:
            response = self._get(f"{origin}/robots.txt", None)
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            return None
        parser = RobotFileParser()
        parser.parse(_decode(response).splitlines())
        return parser

    def _record(self, url: str, source_name: str, kind: str, **values) -> None:
        body = values.get("body", "")
        values.setdefault("status_code", None)
        values.setdefault("error", "")
        values["body"] = body
        values["content_hash"] = hashlib.sha256(body.encode()).hexdigest() if body else ""
        FetchedPage.objects.update_or_create(
            url=url, defaults={"source_name": source_name, "kind": kind, **values}
        )
