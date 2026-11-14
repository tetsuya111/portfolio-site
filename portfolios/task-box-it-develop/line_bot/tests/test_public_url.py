"""公開URLの解決（ngrok）と、LINEのWebhookエンドポイントの自動設定。

ngrokのローカルAPIもLINE Messaging API も実際には呼ばない。
"""

import httpx
import pytest

from app import public_url
from app.config import reset_settings
from app.startup import configure_public_url


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def tunnels(*items):
    return {"tunnels": list(items)}


def tunnel(url: str, name: str = "command_line", proto: str = "https"):
    return {"name": name, "public_url": url, "proto": proto}


@pytest.fixture
def ngrok(monkeypatch):
    """ngrokのローカルAPIの応答を差し替える。呼び出し回数も数える。"""

    class Api:
        def __init__(self):
            self.response = FakeResponse(tunnels(tunnel("https://sample.ngrok-free.app")))
            self.calls = 0

        def get(self, url, timeout=None):
            self.calls += 1
            if isinstance(self.response, Exception):
                raise self.response
            return self.response

    api = Api()
    monkeypatch.setattr(public_url.httpx, "get", api.get)
    yield api
    public_url.set_current("")


@pytest.fixture
def use_ngrok(monkeypatch):
    monkeypatch.setenv("USE_NGROK", "true")
    reset_settings()
    yield
    reset_settings()


class TestResolve:
    def test_without_ngrok_uses_the_fixed_url(self, monkeypatch, ngrok):
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://bot.example.com/")
        reset_settings()
        assert public_url.resolve() == "https://bot.example.com"
        # ngrokのAPIは呼ばない
        assert ngrok.calls == 0

    def test_trailing_slash_does_not_matter(self):
        assert public_url.normalize("https://a.example.com/") == public_url.normalize(
            " https://a.example.com "
        )

    def test_with_ngrok_uses_the_tunnel_url(self, use_ngrok, ngrok):
        assert public_url.resolve() == "https://sample.ngrok-free.app"
        assert public_url.webhook_url() == "https://sample.ngrok-free.app/webhook"
        assert public_url.liff_endpoint_url() == "https://sample.ngrok-free.app/liff"

    def test_tunnel_is_chosen_by_name(self, use_ngrok, ngrok, monkeypatch):
        ngrok.response = FakeResponse(tunnels(
            tunnel("https://first.ngrok-free.app", name="other"),
            tunnel("https://named.ngrok-free.app", name="line_bot"),
        ))
        monkeypatch.setenv("NGROK_TUNNEL_NAME", "line_bot")
        reset_settings()
        assert public_url.resolve() == "https://named.ngrok-free.app"

    def test_http_only_tunnel_is_skipped(self, use_ngrok, ngrok, monkeypatch, caplog):
        ngrok.response = FakeResponse(tunnels(tunnel("http://plain.ngrok-free.app", proto="http")))
        monkeypatch.setenv("PUBLIC_BASE_URL", "")
        reset_settings()
        with caplog.at_level("WARNING"):
            assert public_url.resolve() == ""
        assert "httpsのトンネルが見つかりません" in caplog.text

    def test_connection_error_falls_back_to_the_fixed_url(
        self, use_ngrok, ngrok, monkeypatch, caplog
    ):
        ngrok.response = httpx.ConnectError("refused")
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://fallback.example.com")
        reset_settings()
        with caplog.at_level("WARNING"):
            assert public_url.resolve() == "https://fallback.example.com"
        assert "ngrokが起動していない可能性" in caplog.text

    def test_non_https_url_is_warned(self, monkeypatch, caplog):
        monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8100")
        reset_settings()
        with caplog.at_level("WARNING"):
            assert public_url.resolve() == "http://localhost:8100"
        assert "HTTPSではありません" in caplog.text

    def test_empty_url_is_allowed(self, monkeypatch):
        monkeypatch.setenv("PUBLIC_BASE_URL", "")
        reset_settings()
        assert public_url.resolve() == ""
        assert public_url.webhook_url() == ""


class TestWebhookEndpoint:
    def test_without_ngrok_line_api_is_not_called(self, line, monkeypatch):
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://bot.example.com")
        reset_settings()
        configure_public_url()
        assert line.endpoint_updates == []
        assert line.endpoint_tests == 0

    def test_endpoint_is_updated_and_tested(self, line, use_ngrok, ngrok):
        configure_public_url()
        assert line.endpoint_updates == ["https://sample.ngrok-free.app/webhook"]
        assert line.endpoint_tests == 1

    def test_same_endpoint_is_not_updated(self, line, use_ngrok, ngrok):
        line.webhook_endpoint = "https://sample.ngrok-free.app/webhook"
        configure_public_url()
        assert line.endpoint_updates == []
        assert line.endpoint_tests == 0

    def test_update_failure_does_not_stop_startup(self, line, use_ngrok, ngrok, caplog):
        from app.line.client import LineApiError

        def boom(url):
            raise LineApiError("403")

        line.set_webhook_endpoint = boom
        with caplog.at_level("WARNING"):
            configure_public_url()  # 例外を外に出さない
        assert "LINE Developers で次のURLを設定してください" in caplog.text

    def test_failed_connection_test_is_logged(self, line, use_ngrok, ngrok, caplog):
        line.test_result = False
        with caplog.at_level("WARNING"):
            configure_public_url()
        assert "疎通確認に失敗" in caplog.text

    def test_no_url_means_no_update(self, line, use_ngrok, ngrok, monkeypatch, caplog):
        ngrok.response = httpx.ConnectError("refused")
        monkeypatch.setenv("PUBLIC_BASE_URL", "")
        reset_settings()
        with caplog.at_level("WARNING"):
            configure_public_url()
        assert line.endpoint_updates == []
        assert "ngrok http 8100" in caplog.text

    def test_production_with_ngrok_is_warned(self, line, use_ngrok, ngrok, monkeypatch, caplog):
        monkeypatch.setenv("ENVIRONMENT", "production")
        reset_settings()
        with caplog.at_level("WARNING"):
            configure_public_url()
        assert "本番では無効にしてください" in caplog.text

    def test_missing_access_token_is_reported_without_crashing(
        self, line, use_ngrok, ngrok, monkeypatch, caplog
    ):
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        reset_settings()
        with caplog.at_level("WARNING"):
            configure_public_url()
        assert "LINE_CHANNEL_ACCESS_TOKEN が未設定" in caplog.text
        assert line.endpoint_updates == []

    def test_unexpected_error_does_not_stop_startup(self, line, use_ngrok, ngrok, caplog):
        def boom():
            raise RuntimeError("想定外")

        line.get_webhook_endpoint = boom
        with caplog.at_level("WARNING"):
            configure_public_url()  # 起動を止めない
        assert "公開URLの設定に失敗しました" in caplog.text

    def test_startup_shows_the_links(self, line, use_ngrok, ngrok, caplog):
        with caplog.at_level("INFO"):
            configure_public_url()
        # 公開URL・Webhook・ngrokの管理画面が起動時に出る
        assert "https://sample.ngrok-free.app" in caplog.text
        assert "https://sample.ngrok-free.app/webhook" in caplog.text
        assert "http://127.0.0.1:4040" in caplog.text

    def test_links_are_shown_without_ngrok_too(self, line, monkeypatch, caplog):
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://bot.example.com")
        reset_settings()
        with caplog.at_level("INFO"):
            configure_public_url()
        assert "https://bot.example.com/webhook" in caplog.text
        assert "4040" not in caplog.text  # ngrokを使わないときは管理画面を出さない

    def test_liff_endpoint_is_reported(self, line, use_ngrok, ngrok, monkeypatch, caplog):
        monkeypatch.setenv("LIFF_ID", "1234-abcd")
        reset_settings()
        with caplog.at_level("INFO"):
            configure_public_url()
        assert "https://sample.ngrok-free.app/liff" in caplog.text


class TestHealthz:
    def test_healthz_shows_the_public_url(self, api, monkeypatch):
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://bot.example.com")
        reset_settings()
        public_url.resolve()
        body = api.get("/healthz").json()
        assert body["public_url"] == "https://bot.example.com"
        assert body["ngrok"] is False
        public_url.set_current("")
