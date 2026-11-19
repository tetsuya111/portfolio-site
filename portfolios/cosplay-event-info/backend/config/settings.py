"""コスプレイベント情報まとめサイトの Django 設定。

値は環境変数で切り替える（.env.example を参照）。
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# 空文字の環境変数（.env の値が空など）は未設定として既定値を使う
APP_ENV = os.environ.get("APP_ENV") or "development"
_DEV_ENVS = {"development", "test"}

# 開発・テスト専用の固定鍵。本番（APP_ENV が development・test 以外）では使わない。
_DEV_SECRET_KEY = "dev-only-insecure-secret-key-for-cosplay-event-info"  # noqa: S105


def build_secret_key(env: str, value: str | None) -> str:
    """SECRET_KEY を決める。本番で未設定なら起動を中止する（NF-3）。"""
    if value:
        return value
    if env in _DEV_ENVS:
        return _DEV_SECRET_KEY
    raise ImproperlyConfigured("本番環境では DJANGO_SECRET_KEY を設定してください。")


SECRET_KEY = build_secret_key(APP_ENV, os.environ.get("DJANGO_SECRET_KEY"))
DEBUG = APP_ENV == "development"
ALLOWED_HOSTS = [
    h.strip()
    for h in (os.environ.get("ALLOWED_HOSTS") or "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "catalog",
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
        "NAME": os.environ.get("DATABASE_PATH") or str(BASE_DIR / "cosplay.db"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in (os.environ.get("CORS_ORIGINS") or "http://localhost:3000").split(",")
    if o.strip()
]
CORS_ALLOW_METHODS = ["GET", "OPTIONS"]

REST_FRAMEWORK = {
    # API は匿名の読み取り専用（書き込みはバッチと管理画面だけ）
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "UNAUTHENTICATED_USER": None,
}

# 収集処理の設定
EVENT_SIMILARITY_THRESHOLD = 0.85
COSPLAYER_SIMILARITY_THRESHOLD = 0.9
FETCH_MIN_INTERVAL = float(os.environ.get("FETCH_MIN_INTERVAL") or "1.0")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"catalog": {"handlers": ["console"], "level": "INFO"}},
}
