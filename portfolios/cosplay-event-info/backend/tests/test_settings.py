import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings import build_secret_key


def test_production_without_secret_raises():
    with pytest.raises(ImproperlyConfigured):
        build_secret_key("production", None)


def test_production_with_empty_secret_raises():
    with pytest.raises(ImproperlyConfigured):
        build_secret_key("production", "")


def test_production_uses_given_secret():
    assert build_secret_key("production", "s" * 50) == "s" * 50


def test_development_uses_dev_key():
    key = build_secret_key("development", None)

    assert isinstance(key, str)
    assert key


def test_empty_env_values_fall_back_to_defaults(monkeypatch):
    import importlib

    import config.settings as settings_module

    monkeypatch.setenv("DATABASE_PATH", "")
    monkeypatch.setenv("FETCH_MIN_INTERVAL", "")
    monkeypatch.setenv("ALLOWED_HOSTS", "")
    try:
        reloaded = importlib.reload(settings_module)
        assert reloaded.DATABASES["default"]["NAME"].endswith("cosplay.db")
        assert reloaded.FETCH_MIN_INTERVAL == 1.0
        assert reloaded.ALLOWED_HOSTS == ["localhost", "127.0.0.1"]
    finally:
        monkeypatch.undo()
        importlib.reload(settings_module)
