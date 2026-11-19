"""対象サイトのページ取得。robots.txt・アクセス間隔・取得ページのログを扱う。

対応要件: REQ-1.4〜1.6, REQ-2
"""

from __future__ import annotations

import enum
import hashlib
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from django.conf import settings

from events.models import FetchedPage

logger = logging.getLogger(__name__)

USER_AGENT = "av-event-db-crawler/0.1"
TIMEOUT_SECONDS = 10.0
MAX_REDIRECTS = 5
_META_CHARSET = re.compile(rb"""<meta[^>]+charset=["']?([\w-]+)""", re.IGNORECASE)


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _disallow_all() -> RobotFileParser:
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /"])
    return parser


class _RedirectDisallowedError(Exception):
    """リダイレクト先が robots.txt で禁止されている。"""


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
        retry_unparsed: bool = False,
    ) -> None:
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)
        self._min_interval = settings.FETCH_MIN_INTERVAL if min_interval is None else min_interval
        self._sleep = sleep
        self._clock = clock
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        # 取得済みとして再取得しない結果（解析できなかったページは抽出ルール修正後に
        # --retry-unparsed で取り直す）
        self._done = [FetchedPage.Result.SUCCESS]
        if not retry_unparsed:
            self._done.append(FetchedPage.Result.UNPARSED)

    def close(self) -> None:
        self._client.close()

    def fetch(
        self, url: str, source_name: str, kind: str, cookies: dict[str, str] | None = None
    ) -> FetchResult:
        if (
            kind == FetchedPage.Kind.DETAIL
            and FetchedPage.objects.filter(url=url, result__in=self._done).exists()
        ):
            return FetchResult(FetchStatus.SKIPPED)

        if not self._allowed(url):
            self._record(url, source_name, kind, result=FetchedPage.Result.DISALLOWED)
            return FetchResult(FetchStatus.DISALLOWED)

        try:
            response = self._get(url, cookies)
        except _RedirectDisallowedError as exc:
            self._record(
                url, source_name, kind, result=FetchedPage.Result.DISALLOWED, error=str(exc)
            )
            return FetchResult(FetchStatus.DISALLOWED)
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

    def mark_unparsed(self, url: str, error: str) -> None:
        """取得はできたがイベントを抽出できなかったページ。既定では再取得しない。"""
        FetchedPage.objects.filter(url=url).update(result=FetchedPage.Result.UNPARSED, error=error)

    def mark_failed(self, url: str, error: str) -> None:
        """取得はできたが保存に失敗したページを失敗扱いにし、次回再取得させる。"""
        FetchedPage.objects.filter(url=url).update(result=FetchedPage.Result.FAILED, error=error)

    def _get(self, url: str, cookies: dict[str, str] | None) -> httpx.Response:
        """リダイレクトを1回ずつ辿り、各リダイレクト先も robots.txt で確認する（REQ-1.6）。

        Cookie は元のURLと同じオリジン（スキーム＋ホスト）にだけ送る。
        """
        origin = origin_of(url)
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            # https→http の格下げや別ホストへは Cookie を送らない
            same_origin = origin_of(current) == origin
            response = self._request(current, cookies if same_origin else None)
            if not response.is_redirect:
                return response
            location = response.headers.get("location", "")
            target = urljoin(current, location)
            if urlsplit(target).scheme not in ("http", "https"):
                raise httpx.TooManyRedirects(f"不正なリダイレクト先: {location}", request=None)
            if not self._allowed(target):
                raise _RedirectDisallowedError(f"リダイレクト先が robots.txt で禁止: {target}")
            current = target
        raise httpx.TooManyRedirects("リダイレクトが多すぎます", request=None)

    def _request(self, url: str, cookies: dict[str, str] | None) -> httpx.Response:
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
                url, headers=headers, follow_redirects=False, timeout=TIMEOUT_SECONDS
            )
        finally:
            self._last_request[host] = self._clock()

    def _allowed(self, url: str) -> bool:
        origin = origin_of(url)
        if origin not in self._robots:
            self._robots[origin] = self._load_robots(origin)
        parser = self._robots[origin]
        return parser is None or parser.can_fetch(USER_AGENT, url)

    def _load_robots(self, origin: str) -> RobotFileParser | None:
        """robots.txt を読む（RFC 9309 に沿う）。

        - リダイレクトは最大5回辿る
        - 4xx（存在しない）は制限なし（None）
        - 5xx・通信エラーは一時的に読めないため、すべて禁止とみなす
        """
        url = f"{origin}/robots.txt"
        try:
            for _ in range(MAX_REDIRECTS + 1):
                response = self._request(url, None)
                if not response.is_redirect:
                    break
                url = urljoin(url, response.headers.get("location", ""))
                if urlsplit(url).scheme not in ("http", "https"):
                    return _disallow_all()
            else:
                return _disallow_all()
        except httpx.HTTPError:
            return _disallow_all()
        if 400 <= response.status_code < 500:
            return None
        if response.status_code != 200:
            return _disallow_all()
        parser = RobotFileParser()
        parser.parse(_decode(response).splitlines())
        return parser

    def _record(self, url: str, source_name: str, kind: str, **values) -> None:
        if values["result"] != FetchedPage.Result.SUCCESS:
            logger.warning(
                "[%s] 取得できませんでした（%s）: %s %s",
                source_name,
                values["result"],
                url,
                values.get("error", ""),
            )
        body = values.get("body", "")
        values.setdefault("status_code", None)
        values.setdefault("error", "")
        values["body"] = body
        values["content_hash"] = hashlib.sha256(body.encode()).hexdigest() if body else ""
        FetchedPage.objects.update_or_create(
            url=url, defaults={"source_name": source_name, "kind": kind, **values}
        )
