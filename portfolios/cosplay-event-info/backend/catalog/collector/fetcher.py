"""ページの取得と取得ログの記録（FT-1〜FT-4、NF-1）。"""

import logging
import time
from collections.abc import Callable
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from catalog.models import FetchedPage

logger = logging.getLogger(__name__)

USER_AGENT = "cosplay-event-info-bot/0.1"
REQUEST_TIMEOUT = 30.0


class Fetcher:
    """robots.txt とリクエスト間隔を守ってページを取得し、結果を FetchedPage に残す。"""

    def __init__(
        self,
        client: httpx.Client,
        *,
        min_interval: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client
        self.min_interval = min_interval
        self._sleep = sleep
        self._clock = clock
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}

    def fetch(self, url: str, kind: str, *, force: bool = False) -> FetchedPage | None:
        """ページを取得する。取得済み・robots.txt で禁止・失敗のときは None を返す。"""
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            logger.warning("http(s) 以外の URL は取得しません: %s", url)
            return None
        if not force and self._already_fetched(url):
            logger.info("取得済みのためスキップ: %s", url)
            return None
        if not self._allowed(url):
            logger.info("robots.txt で禁止されているためスキップ: %s", url)
            return None

        try:
            response = self._get(url)
        except httpx.HTTPError as exc:
            logger.warning("取得に失敗: %s (%s)", url, exc)
            self._save(url, kind, status_code=None, content="", error=str(exc) or repr(exc))
            return None

        if not response.is_success:
            logger.warning("取得に失敗: %s (HTTP %s)", url, response.status_code)
            self._save(url, kind, response.status_code, "", f"HTTP {response.status_code}")
            return None
        return self._save(url, kind, response.status_code, response.text, "")

    # ---- 内部処理 ----

    @staticmethod
    def _already_fetched(url: str) -> bool:
        return FetchedPage.objects.filter(
            url=url, status_code__gte=200, status_code__lt=300
        ).exists()

    def _get(self, url: str) -> httpx.Response:
        host = urlsplit(url).netloc
        last = self._last_request.get(host)
        if last is not None:
            wait = self.min_interval - (self._clock() - last)
            if wait > 0:
                self._sleep(wait)
        try:
            return self.client.get(
                url,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=REQUEST_TIMEOUT,
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
        """robots.txt を読む。取得できない場合は None（制限なし）とする。"""
        try:
            response = self._get(f"{origin}/robots.txt")
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            return None
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser

    @staticmethod
    def _save(
        url: str, kind: str, status_code: int | None, content: str, error: str
    ) -> FetchedPage:
        page, _ = FetchedPage.objects.update_or_create(
            url=url,
            defaults={
                "kind": kind,
                "status_code": status_code,
                "content": content,
                "error": error,
            },
        )
        return page
