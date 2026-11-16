import pytest

from app.config import DEV_JWT_SECRET, Settings
from app.main import create_app


def test_production_requires_strong_secret():
    with pytest.raises(ValueError):
        Settings(app_env="production", jwt_secret="x" * 31).validate_for_env()
    Settings(app_env="production", jwt_secret="x" * 32).validate_for_env()


def test_production_rejects_default_secret():
    with pytest.raises(ValueError):
        Settings(app_env="production").validate_for_env()


def test_development_allows_default_secret():
    Settings(app_env="development").validate_for_env()


def test_cors_origins_parsed_from_comma_string(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.example, http://b.example")
    assert Settings().cors_origins == ["http://a.example", "http://b.example"]


def test_empty_secret_is_treated_as_unset():
    assert Settings(jwt_secret="").jwt_secret == DEV_JWT_SECRET
    with pytest.raises(ValueError):
        Settings(app_env="production", jwt_secret="  ").validate_for_env()


def test_create_app_refuses_weak_production_secret():
    with pytest.raises(ValueError):
        create_app(Settings(app_env="production", jwt_secret="short"))
