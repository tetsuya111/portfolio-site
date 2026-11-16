import httpx
import pytest

from app.batch.fetcher import MAX_BYTES, Fetcher, FetchError

URL = "https://billboard.mryogaku.com/php/dispHot100.php?date=2025-11-15"


def _fetcher(handler):
    return Fetcher(transport=httpx.MockTransport(handler))


def test_get_returns_text():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, text="<html>ok</html>")

    assert _fetcher(handler).get(URL) == "<html>ok</html>"
    assert seen["url"] == URL


def test_redirect_is_error():
    def handler(request):
        return httpx.Response(302, headers={"Location": "https://evil.example/"})

    with pytest.raises(FetchError):
        _fetcher(handler).get(URL)


def test_non_200_is_error():
    with pytest.raises(FetchError):
        _fetcher(lambda r: httpx.Response(500)).get(URL)


@pytest.mark.parametrize(
    "url", ["https://evil.example/", "http://billboard.mryogaku.com/", "file:///etc/passwd"]
)
def test_rejects_other_host(url):
    def handler(request):  # pragma: no cover - 呼ばれてはならない
        raise AssertionError("request must not be sent")

    with pytest.raises(FetchError):
        _fetcher(handler).get(url)


def test_too_large_is_error():
    body = b"a" * (MAX_BYTES + 1)
    with pytest.raises(FetchError):
        _fetcher(lambda r: httpx.Response(200, content=body)).get(URL)


def test_network_error_is_fetch_error():
    def handler(request):
        raise httpx.ConnectTimeout("timeout")

    with pytest.raises(FetchError):
        _fetcher(handler).get(URL)
