import pytest

from app.config import ConfigError, load_settings

HTTPS_FRONTEND = "https://example.com"
HTTPS_REDIRECT = "https://example.com/auth/callback"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("FRONTEND_URL", "SPOTIFY_REDIRECT_URI", "COOKIE_SECURE"):
        monkeypatch.delenv(name, raising=False)


def _https(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", HTTPS_FRONTEND)
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", HTTPS_REDIRECT)


def test_cookie_secure_explicit_true(monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "TRUE")
    assert load_settings().cookie_secure is True


def test_cookie_secure_explicit_false_with_https(monkeypatch):
    _https(monkeypatch)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    assert load_settings().cookie_secure is False


def test_cookie_secure_default_follows_https(monkeypatch):
    assert load_settings().cookie_secure is False
    _https(monkeypatch)
    assert load_settings().cookie_secure is True


def test_cookie_secure_invalid_value(monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "yes")
    with pytest.raises(ConfigError):
        load_settings()


def test_http_non_loopback_frontend_rejected(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "http://example.com")
    with pytest.raises(ConfigError):
        load_settings()


def test_http_non_loopback_redirect_rejected(monkeypatch):
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://example.com/auth/callback")
    with pytest.raises(ConfigError):
        load_settings()


def test_unsupported_scheme_rejected(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "ftp://127.0.0.1")
    with pytest.raises(ConfigError):
        load_settings()


@pytest.mark.parametrize("url", ["http://localhost:3000", "http://[::1]:3000"])
def test_http_loopback_allowed(monkeypatch, url):
    monkeypatch.setenv("FRONTEND_URL", url)
    assert load_settings().frontend_url == url
