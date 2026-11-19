import httpx
import pytest

from events.crawler.fetcher import FetchStatus, PageFetcher
from events.models import FetchedPage

pytestmark = pytest.mark.django_db


class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps: list[float] = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def make_fetcher(handler, robots="", clock=None):
    requests: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots) if robots else httpx.Response(404)
        return handler(request)

    clock = clock or FakeClock()
    client = httpx.Client(transport=httpx.MockTransport(wrapped))
    fetcher = PageFetcher(client=client, min_interval=1.0, sleep=clock.sleep, clock=clock.time)
    return fetcher, requests


def ok(request):
    return httpx.Response(200, text="<h1>hello</h1>", headers={"content-type": "text/html"})


def page_requests(requests):
    return [r for r in requests if r.url.path != "/robots.txt"]


def test_fetch_records_page():
    fetcher, _ = make_fetcher(ok)
    res = fetcher.fetch("https://a.example.com/event/1", "site", "detail")
    assert res.status is FetchStatus.FETCHED
    assert res.body == "<h1>hello</h1>"
    page = FetchedPage.objects.get(url="https://a.example.com/event/1")
    assert page.result == "success"
    assert page.status_code == 200
    assert page.kind == "detail"
    assert page.body == "<h1>hello</h1>"
    assert len(page.content_hash) == 64


def test_successful_detail_page_is_not_requested_again():
    fetcher, requests = make_fetcher(ok)
    fetcher.fetch("https://a.example.com/event/1", "site", "detail")
    res = fetcher.fetch("https://a.example.com/event/1", "site", "detail")
    assert res.status is FetchStatus.SKIPPED
    assert len(page_requests(requests)) == 1


def test_already_fetched_detail_page_in_previous_run_is_skipped():
    FetchedPage.objects.create(
        url="https://a.example.com/event/1", source_name="site", kind="detail", result="success"
    )
    fetcher, requests = make_fetcher(ok)
    assert fetcher.fetch("https://a.example.com/event/1", "site", "detail").status is (
        FetchStatus.SKIPPED
    )
    assert requests == []


def test_failed_detail_page_is_retried():
    FetchedPage.objects.create(
        url="https://a.example.com/event/1", source_name="site", kind="detail", result="failed"
    )
    fetcher, requests = make_fetcher(ok)
    assert fetcher.fetch("https://a.example.com/event/1", "site", "detail").status is (
        FetchStatus.FETCHED
    )
    assert FetchedPage.objects.get().result == "success"


def test_list_page_is_fetched_every_time():
    fetcher, requests = make_fetcher(ok)
    fetcher.fetch("https://a.example.com/list/", "site", "list")
    res = fetcher.fetch("https://a.example.com/list/", "site", "list")
    assert res.status is FetchStatus.FETCHED
    assert len(page_requests(requests)) == 2
    assert FetchedPage.objects.count() == 1


def test_robots_disallow():
    fetcher, requests = make_fetcher(ok, robots="User-agent: *\nDisallow: /private/\n")
    res = fetcher.fetch("https://a.example.com/private/1", "site", "detail")
    assert res.status is FetchStatus.DISALLOWED
    assert page_requests(requests) == []
    assert FetchedPage.objects.get().result == "disallowed"
    # robots.txt はホストごとに1回だけ読む
    fetcher.fetch("https://a.example.com/public/1", "site", "detail")
    assert sum(r.url.path == "/robots.txt" for r in requests) == 1


def test_server_error_is_recorded_as_failed():
    fetcher, _ = make_fetcher(lambda r: httpx.Response(503))
    res = fetcher.fetch("https://a.example.com/event/1", "site", "detail")
    assert res.status is FetchStatus.FAILED
    page = FetchedPage.objects.get()
    assert page.result == "failed"
    assert page.status_code == 503
    assert "503" in page.error


def test_network_error_is_recorded_as_failed():
    def boom(request):
        raise httpx.ConnectError("down", request=request)

    fetcher, _ = make_fetcher(boom)
    res = fetcher.fetch("https://a.example.com/event/1", "site", "detail")
    assert res.status is FetchStatus.FAILED
    assert "down" in FetchedPage.objects.get().error


def test_waits_between_requests_to_same_host():
    clock = FakeClock()
    fetcher, _ = make_fetcher(ok, clock=clock)
    fetcher.fetch("https://a.example.com/1", "site", "list")
    fetcher.fetch("https://a.example.com/2", "site", "list")
    fetcher.fetch("https://b.example.com/1", "site", "list")
    # 同じホストへの連続リクエスト（robots → a/1 → a/2、robots → b/1）の間だけ待つ。
    # b の robots.txt は a の直後でも待たない（3回で4回ではない）
    assert clock.sleeps == [1.0, 1.0, 1.0]


def test_sends_cookies_and_user_agent():
    seen = {}

    def handler(request):
        seen["cookie"] = request.headers.get("cookie")
        seen["ua"] = request.headers.get("user-agent")
        return ok(request)

    fetcher, _ = make_fetcher(handler)
    fetcher.fetch("https://a.example.com/1", "site", "list", cookies={"age_check_done": "1"})
    assert seen["cookie"] == "age_check_done=1"
    assert seen["ua"].startswith("av-event-db-crawler/")


def test_decodes_shift_jis_by_meta_charset():
    body = '<meta charset="Shift_JIS"><h1>サイン会</h1>'.encode("shift_jis")

    def handler(request):
        return httpx.Response(200, content=body, headers={"content-type": "text/html"})

    fetcher, _ = make_fetcher(handler)
    assert "サイン会" in fetcher.fetch("https://a.example.com/1", "site", "list").body
