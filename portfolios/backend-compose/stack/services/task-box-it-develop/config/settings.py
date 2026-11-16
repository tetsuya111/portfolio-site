"""Django settings. 環境依存の値はすべて環境変数（backend/.env）から読む。詳細は docs/backend.md。"""

import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


DEBUG = env_bool("DEBUG", False)
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG and "test" not in sys.argv:
        raise RuntimeError("SECRET_KEY を環境変数で設定してください")
    SECRET_KEY = "dev-only-insecure-secret-key-do-not-use-in-production"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "accounts",
    "agents",
    "chat",
    "summaries",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

# .env の DATABASE_URL が空文字のときも未設定として扱い、SQLite にフォールバックする
DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL")
        or f"sqlite:///{(BASE_DIR / 'db.sqlite3').as_posix()}",
        conn_max_age=60,
    )
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "ja"
# 使用量の「1日」は日本時間で区切る（requirements ストーリー8）
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS（フロントエンドのオリジンのみ許可。リフレッシュトークンのCookieを送るため資格情報つき） ---
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# --- DRF / JWT ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
}

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth/"
REFRESH_COOKIE_SECURE = env_bool("REFRESH_COOKIE_SECURE", not DEBUG)

# --- Google認証 ---
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")

# Googleを使わない開発用ログイン（/api/auth/dev-login/）。DEBUG のときだけ有効にできる
ALLOW_DEV_LOGIN = DEBUG and env_bool("ALLOW_DEV_LOGIN", False)

# --- 管理者 ---
# 管理者のメールアドレスを列挙したテキストファイル。本番ではコードの外の絶対パスを指定する
ADMIN_EMAILS_FILE = os.environ.get("ADMIN_EMAILS_FILE", str(BASE_DIR / "admin_emails.txt"))

# --- LLM ---
LLM_CLIENT_CLASS = os.environ.get("LLM_CLIENT_CLASS", "agents.llm.AnthropicLLMClient")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5")
LLM_EFFORT = os.environ.get("LLM_EFFORT", "medium")
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "32000"))
DAILY_TOKEN_LIMIT = int(os.environ.get("DAILY_TOKEN_LIMIT", "300000"))
MESSAGE_MAX_LENGTH = 4000
# 対話履歴の保持期間。最後のメッセージからこの日数が過ぎた対話は purge_conversations で消す
CONVERSATION_RETENTION_DAYS = int(os.environ.get("CONVERSATION_RETENTION_DAYS", "30"))
# 同じ対話で処理が異常終了した場合に、実行中フラグを無効とみなすまでの秒数
CONVERSATION_LOCK_TIMEOUT_SECONDS = 300

# --- メール ---
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@localhost")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "default"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
