import httpx
import pytest

from catalog.collector.fetcher import Fetcher
from catalog.models import FetchedPage

pytestmark = pytest.mark.django_db

ROBOTS = "User-agent: *\nDisallow: /private/\n"


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.slept = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def make_fetcher(handler, clock=None, min_interval=1.0):
    calls = []

    def recording(request):
        calls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS)
        return handler(request)

    clock = clock or FakeClock()
    client = httpx.Client(transport=httpx.MockTransport(recording))
    fetcher = Fetcher(client, min_interval=min_interval, sleep=clock.sleep, clock=clock.clock)
    return fetcher, calls


def ok(request):
    return httpx.Response(200, text=f"<html>{request.url.path}</html>")


def test_fetch_saves_page():
    fetcher, _ = make_fetcher(ok)

    page = fetcher.fetch("https://example.com/events", "event")

    assert page is not None
    saved = FetchedPage.objects.get(url="https://example.com/events")
    assert saved.status_code == 200
    assert saved.kind == "event"
    assert "/events" in saved.content


def test_fetched_url_is_not_fetched_again():
    fetcher, calls = make_fetcher(ok)
    fetcher.fetch("https://example.com/events", "event")

    second = fetcher.fetch("https://example.com/events", "event")

    assert second is None
    assert calls.count("https://example.com/events") == 1


def test_already_saved_page_from_previous_run_is_skipped():
    FetchedPage.objects.create(url="https://example.com/old", kind="event", status_code=200)
    fetcher, calls = make_fetcher(ok)

    assert fetcher.fetch("https://example.com/old", "event") is None
    assert calls == []


def test_force_refetches():
    fetcher, calls = make_fetcher(ok)
    fetcher.fetch("https://example.com/events", "event")

    page = fetcher.fetch("https://example.com/events", "event", force=True)

    assert page is not None
    assert calls.count("https://example.com/events") == 2
    assert FetchedPage.objects.filter(url="https://example.com/events").count() == 1


def test_failed_page_is_logged_and_retried_next_time():
    fetcher, calls = make_fetcher(lambda r: httpx.Response(404, text="not found"))

    assert fetcher.fetch("https://example.com/missing", "event") is None
    saved = FetchedPage.objects.get(url="https://example.com/missing")
    assert saved.status_code == 404
    assert "404" in saved.error

    fetcher.fetch("https://example.com/missing", "event")
    assert calls.count("https://example.com/missing") == 2


def test_network_error_is_logged():
    def boom(request):
        raise httpx.ConnectError("connection refused", request=request)

    fetcher, _ = make_fetcher(boom)

    assert fetcher.fetch("https://example.com/down", "event") is None
    saved = FetchedPage.objects.get(url="https://example.com/down")
    assert saved.status_code is None
    assert "connection refused" in saved.error


def test_robots_disallowed_is_not_fetched():
    fetcher, calls = make_fetcher(ok)

    assert fetcher.fetch("https://example.com/private/a", "event") is None
    assert "https://example.com/private/a" not in calls
    assert calls.count("https://example.com/robots.txt") == 1


def test_robots_is_fetched_once_per_host():
    fetcher, calls = make_fetcher(ok)
    fetcher.fetch("https://example.com/a", "event")
    fetcher.fetch("https://example.com/b", "event")

    assert calls.count("https://example.com/robots.txt") == 1


def test_waits_between_requests_to_same_host():
    clock = FakeClock()
    fetcher, _ = make_fetcher(ok, clock=clock, min_interval=1.0)

    fetcher.fetch("https://example.com/a", "event")
    fetcher.fetch("https://example.com/b", "event")

    assert sum(clock.slept) >= 1.0


def test_non_http_url_is_rejected():
    fetcher, calls = make_fetcher(ok)

    assert fetcher.fetch("file:///etc/passwd", "event") is None
    assert calls == []


def make_fetcher_with_robots(robots_response, handler=ok):
    calls = []

    def recording(request):
        calls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return robots_response(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(recording))
    return Fetcher(client, min_interval=0, sleep=lambda s: None), calls


def test_robots_server_error_disallows_all():
    fetcher, calls = make_fetcher_with_robots(lambda r: httpx.Response(503))

    assert fetcher.fetch("https://example.com/a", "event") is None
    assert "https://example.com/a" not in calls


def test_robots_unreachable_disallows_all():
    def boom(request):
        raise httpx.ConnectError("down", request=request)

    fetcher, calls = make_fetcher_with_robots(boom)

    assert fetcher.fetch("https://example.com/a", "event") is None
    assert "https://example.com/a" not in calls


def test_robots_not_found_allows_all():
    fetcher, _ = make_fetcher_with_robots(lambda r: httpx.Response(404))

    assert fetcher.fetch("https://example.com/a", "event") is not None


def test_failed_force_refetch_keeps_previous_content():
    responses = iter([httpx.Response(200, text="saved body"), httpx.Response(500)])
    fetcher, _ = make_fetcher(lambda r: next(responses))
    fetcher.fetch("https://example.com/p", "event")

    assert fetcher.fetch("https://example.com/p", "event", force=True) is None

    saved = FetchedPage.objects.get(url="https://example.com/p")
    assert saved.status_code == 200
    assert saved.content == "saved body"
    assert "500" in saved.error


def test_redirect_to_disallowed_host_is_not_followed():
    def handler(request):
        if request.url.host == "a.example":
            if request.url.path == "/robots.txt":
                return httpx.Response(404)
            return httpx.Response(301, headers={"Location": "https://b.example/private/x"})
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS)
        return httpx.Response(200, text="secret")

    calls = []

    def recording(request):
        calls.append(str(request.url))
        return handler(request)

    fetcher = Fetcher(
        httpx.Client(transport=httpx.MockTransport(recording)), min_interval=0, sleep=lambda s: None
    )

    assert fetcher.fetch("https://a.example/start", "event") is None
    assert "https://b.example/private/x" not in calls


def test_redirect_is_followed_and_saved_under_requested_url():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/old":
            return httpx.Response(302, headers={"Location": "/new"})
        return httpx.Response(200, text="moved body")

    fetcher = Fetcher(
        httpx.Client(transport=httpx.MockTransport(handler)), min_interval=0, sleep=lambda s: None
    )

    page = fetcher.fetch("https://a.example/old", "event")

    assert page is not None
    assert page.url == "https://a.example/old"
    assert page.content == "moved body"


def test_redirected_robots_txt_is_followed():
    def handler(request):
        if request.url.path == "/robots.txt" and request.url.host == "a.example":
            return httpx.Response(301, headers={"Location": "https://www.a.example/robots.txt"})
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS)
        return httpx.Response(200, text="body")

    fetcher = Fetcher(
        httpx.Client(transport=httpx.MockTransport(handler)), min_interval=0, sleep=lambda s: None
    )

    assert fetcher.fetch("https://a.example/private/x", "event") is None
    assert fetcher.last_outcome == "disallowed"


def test_final_url_after_redirect_is_saved():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/event/":
            return httpx.Response(301, headers={"Location": "/events/list/"})
        return httpx.Response(200, text="list")

    fetcher = Fetcher(
        httpx.Client(transport=httpx.MockTransport(handler)), min_interval=0, sleep=lambda s: None
    )

    page = fetcher.fetch("https://a.example/event/", "event")

    assert page.url == "https://a.example/event/"
    assert page.final_url == "https://a.example/events/list/"
