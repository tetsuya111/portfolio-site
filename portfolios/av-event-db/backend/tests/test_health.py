from django.conf import settings
from rest_framework.test import APIClient


def test_health_returns_ok():
    res = APIClient().get("/api/health/")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_debug_is_off_by_default():
    assert settings.DEBUG is False
