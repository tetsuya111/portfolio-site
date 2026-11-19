"""AVイベント情報DBサイトの Django 設定。値は環境変数で切り替える（README を参照）。"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# 未設定時は本番扱い（DEBUG 無効・SECRET_KEY 必須）。ローカル開発は scripts/run-backend.mjs が補う
APP_ENV = os.environ.get("APP_ENV", "production")
_DEV_ENVS = {"development", "test"}

# 開発・テスト専用の固定鍵。本番（APP_ENV が development・test 以外）では使わない。
_DEV_SECRET_KEY = "dev-only-insecure-secret-key-for-av-event-db"  # noqa: S105


def build_secret_key(env: str, value: str | None) -> str:
    """SECRET_KEY を決める。本番で未設定なら起動を中止する。"""
    if value:
        return value
    if env in _DEV_ENVS:
        return _DEV_SECRET_KEY
    raise ImproperlyConfigured("本番環境では DJANGO_SECRET_KEY を設定してください。")


def _csv(name: str, default: str) -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


SECRET_KEY = build_secret_key(APP_ENV, os.environ.get("DJANGO_SECRET_KEY"))
DEBUG = APP_ENV == "development"
ALLOWED_HOSTS = _csv("ALLOWED_HOSTS", "localhost,127.0.0.1")
ENABLE_ADMIN = os.environ.get("DJANGO_ENABLE_ADMIN") == "1"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "events",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DATABASE_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

CORS_ALLOWED_ORIGINS = _csv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
CORS_ALLOW_METHODS = ["GET", "OPTIONS"]

REST_FRAMEWORK = {
    # API は匿名の読み取り専用（書き込みはバッチだけ）
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "UNAUTHENTICATED_USER": None,
}

# 収集処理の設定
# REQ-1.5: 同じサイトへの間隔は1秒未満にできない
FETCH_MIN_INTERVAL = max(1.0, float(os.environ.get("FETCH_MIN_INTERVAL", "1.0")))
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
VENUE_NORMALIZER_MODEL = os.environ.get("VENUE_NORMALIZER_MODEL", "claude-opus-5-5")
GOOGLE_MAPS_GEOCODING_API_KEY = os.environ.get("GOOGLE_MAPS_GEOCODING_API_KEY", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
