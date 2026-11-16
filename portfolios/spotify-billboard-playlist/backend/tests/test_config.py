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


def test_cookie_secure_false_rejected_for_non_loopback(monkeypatch):
    _https(monkeypatch)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    with pytest.raises(ConfigError):
        load_settings()


def test_cookie_secure_false_allowed_for_loopback(monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "false")
    assert load_settings().cookie_secure is False


def test_cookie_secure_default_ignores_scheme_case(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "HTTPS://example.com")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", HTTPS_REDIRECT)
    assert load_settings().cookie_secure is True


def test_batch_settings_skip_web_validation(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "http://example.com")
    monkeypatch.setenv("COOKIE_SECURE", "yes")
    assert load_settings(web=False).cookie_secure is False


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
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", url + "/auth/callback")
    assert load_settings().frontend_url == url


SITE_FRONTEND = "https://site.example/apps/spotify-billboard-playlist"


def _site(monkeypatch, frontend=SITE_FRONTEND, redirect=SITE_FRONTEND + "/auth/callback"):
    monkeypatch.setenv("FRONTEND_URL", frontend)
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", redirect)


def test_public_path_from_frontend_url(monkeypatch):
    _site(monkeypatch, frontend=SITE_FRONTEND + "/")
    assert load_settings().public_path == "/apps/spotify-billboard-playlist"


def test_public_path_empty_without_path(monkeypatch):
    _https(monkeypatch)
    assert load_settings().public_path == ""
    monkeypatch.delenv("FRONTEND_URL")
    monkeypatch.delenv("SPOTIFY_REDIRECT_URI")
    assert load_settings().public_path == ""


@pytest.mark.parametrize("suffix", ["?a=1", "#top"])
def test_frontend_url_with_query_or_fragment_rejected(monkeypatch, suffix):
    _site(monkeypatch, frontend=SITE_FRONTEND + suffix)
    with pytest.raises(ConfigError):
        load_settings()


@pytest.mark.parametrize(
    "redirect",
    [
        # state の Cookie（<パス>/auth）がコールバックに届かない
        "https://site.example/auth/callback",
        "https://other.example/apps/spotify-billboard-playlist/auth/callback",
        "https://site.example/apps/spotify-billboard-playlist/authx/callback",
    ],
)
def test_redirect_uri_outside_state_cookie_rejected(monkeypatch, redirect):
    _site(monkeypatch, redirect=redirect)
    with pytest.raises(ConfigError):
        load_settings()


def test_redirect_uri_with_other_scheme_rejected(monkeypatch):
    # https の FRONTEND_URL では state の Cookie に Secure が付き、http のコールバックには届かない
    monkeypatch.setenv("FRONTEND_URL", "https://localhost:3000")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://localhost:3000/auth/callback")
    with pytest.raises(ConfigError):
        load_settings()


def test_redirect_uri_mismatch_within_cookie_scope_warns(monkeypatch, caplog):
    # Cookie はポートを区別しないため届くが、想定と違う構成なので警告だけ出す
    monkeypatch.setenv("FRONTEND_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/auth/callback")
    with caplog.at_level("WARNING", logger="app.config"):
        load_settings()
    assert "SPOTIFY_REDIRECT_URI" in caplog.text


def test_redirect_uri_match_does_not_warn(monkeypatch, caplog):
    _site(monkeypatch)
    with caplog.at_level("WARNING", logger="app.config"):
        load_settings()
    assert caplog.text == ""
