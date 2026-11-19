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
