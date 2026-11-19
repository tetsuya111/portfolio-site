"""ページの取得と取得ログの記録（FT-1〜FT-4、NF-1）。"""

import logging
import time
from collections.abc import Callable
from typing import Literal
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from catalog.collector.parsers import is_http_url
from catalog.models import FetchedPage

logger = logging.getLogger(__name__)

USER_AGENT = "cosplay-event-info-bot/0.1"
REQUEST_TIMEOUT = 30.0
MAX_REDIRECTS = 5

# fetch の結果。None を返したときの理由を呼び出し側が区別するために使う。
Outcome = Literal["fetched", "skipped", "disallowed", "failed"]


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
        # None は制限なし、False はすべて禁止（robots.txt がサーバーエラー・接続不可）
        self._robots: dict[str, RobotFileParser | Literal[False] | None] = {}
        self.last_outcome: Outcome | None = None

    def fetch(self, url: str, kind: str, *, force: bool = False) -> FetchedPage | None:
        """ページを取得する。取得済み・robots.txt で禁止・失敗のときは None を返す。

        None を返した理由は last_outcome（skipped / disallowed / failed）で分かる。
        """
        page, self.last_outcome = self._fetch(url, kind, force)
        return page

    def _fetch(self, url: str, kind: str, force: bool) -> tuple[FetchedPage | None, Outcome]:
        if not is_http_url(url):
            logger.warning("http(s) 以外の URL は取得しません: %s", url)
            return None, "disallowed"
        if not force and self._already_fetched(url):
            logger.info("取得済みのためスキップ: %s", url)
            return None, "skipped"

        current = url
        for _ in range(MAX_REDIRECTS + 1):
            # リダイレクト先も含め、リクエストのたびにそのホストの robots.txt と間隔を守る
            if not is_http_url(current) or not self._allowed(current):
                logger.info("robots.txt で禁止されているためスキップ: %s", current)
                return None, "disallowed"
            try:
                response = self._get(current)
            except httpx.HTTPError as exc:
                logger.warning("取得に失敗: %s (%s)", current, exc)
                self._save(url, kind, status_code=None, content="", error=str(exc) or repr(exc))
                return None, "failed"
            location = response.headers.get("Location")
            if not (response.is_redirect and location):
                break
            current = urljoin(current, location)
        else:
            self._save(url, kind, None, "", "リダイレクトが多すぎます")
            return None, "failed"

        if not response.is_success:
            logger.warning("取得に失敗: %s (HTTP %s)", current, response.status_code)
            self._save(url, kind, response.status_code, "", f"HTTP {response.status_code}")
            return None, "failed"
        page = self._save(url, kind, response.status_code, response.text, "", final_url=current)
        return page, "fetched"

    # ---- 内部処理 ----

    @staticmethod
    def _already_fetched(url: str) -> bool:
        return FetchedPage.objects.filter(
            url=url, status_code__gte=200, status_code__lt=300
        ).exists()

    def _get(self, url: str, *, follow_redirects: bool = False) -> httpx.Response:
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
                follow_redirects=follow_redirects,
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
        if parser is None:
            return True
        if parser is False:
            return False
        return parser.can_fetch(USER_AGENT, url)

    def _load_robots(self, origin: str) -> RobotFileParser | Literal[False] | None:
        """robots.txt を読む（RFC 9309）。

        4xx（置いていない）なら制限なし、5xx・接続できない場合はすべて禁止とみなす。
        """
        try:
            # robots.txt のリダイレクト（http→https、www 付きなど）はたどる（RFC 9309）
            response = self._get(f"{origin}/robots.txt", follow_redirects=True)
        except httpx.HTTPError:
            return False
        if response.status_code >= 500:
            return False
        if response.status_code != 200:
            return None
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser

    @staticmethod
    def _save(
        url: str, kind: str, status_code: int | None, content: str, error: str, final_url: str = ""
    ) -> FetchedPage:
        failed = status_code is None or not 200 <= status_code < 300
        previous = FetchedPage.objects.filter(url=url).first()
        if failed and previous and previous.is_success:
            # --force の再取得に失敗した場合は、前回取得できた本文を残してエラーだけ記録する
            previous.error = error
            previous.save(update_fields=["error", "fetched_at"])
            return previous
        page, _ = FetchedPage.objects.update_or_create(
            url=url,
            defaults={
                "kind": kind,
                "status_code": status_code,
                "content": content,
                "error": error,
                "final_url": final_url if final_url != url else "",
            },
        )
        return page
