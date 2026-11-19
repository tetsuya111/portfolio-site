from django.conf import settings
from rest_framework.test import APIClient


def test_health_returns_ok():
    res = APIClient().get("/api/health/")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_debug_is_off_by_default():
    assert settings.DEBUG is False


def test_secret_key_is_required_in_production():
    import pytest
    from django.core.exceptions import ImproperlyConfigured

    from config.settings import build_secret_key

    with pytest.raises(ImproperlyConfigured):
        build_secret_key("production", None)
    assert build_secret_key("production", "k") == "k"
