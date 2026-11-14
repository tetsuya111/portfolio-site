"""環境変数から読む設定。詳細は docs/line-bot.md を参照。"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _str(name: str, default: str = "") -> str:
    """.env.example をコピーした直後は `KEY=`（空文字）になる。空文字は未設定として扱う。"""
    return os.environ.get(name, "").strip() or default


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class Settings:
    def __init__(self) -> None:
        # LINE
        self.channel_secret = _str("LINE_CHANNEL_SECRET")
        self.channel_access_token = _str("LINE_CHANNEL_ACCESS_TOKEN")
        self.liff_id = _str("LIFF_ID")
        # 保存先。本番は PostgreSQL。未設定なら開発用に SQLite を使う
        self.database_url = _str("DATABASE_URL", f"sqlite:///{BASE_DIR / 'line_bot.sqlite3'}")
        self.redis_url = _str("REDIS_URL", "redis://localhost:6379/0")
        # LLM
        self.anthropic_api_key = _str("ANTHROPIC_API_KEY")
        self.llm_model = _str("LLM_MODEL", "claude-sonnet-5")
        self.llm_max_tokens = _int("LLM_MAX_TOKENS", 1000)
        self.llm_client_class = _str("LLM_CLIENT_CLASS", "app.agents.llm.AnthropicLLMClient")
        self.daily_llm_call_limit = _int("DAILY_LLM_CALL_LIMIT", 30)
        # 案内先のURL（未設定なら「機能改修中」と返す）
        self.contract_page_url = _str("CONTRACT_PAGE_URL")
        self.hearing_site_url = _str("HEARING_SITE_URL")
        # 公開URL（インターネットからこのアプリに届くURL）
        # USE_NGROK は開発用。true のときだけ ngrok から取得し、LINEのWebhook設定を書き換える
        self.use_ngrok = _bool("USE_NGROK", False)
        self.public_base_url = _str("PUBLIC_BASE_URL")
        self.ngrok_api_url = _str("NGROK_API_URL", "http://127.0.0.1:4040/api/tunnels")
        self.ngrok_tunnel_name = _str("NGROK_TUNNEL_NAME")
        self.environment = _str("ENVIRONMENT", "development")
        # 保持期間
        self.history_retention_hours = _int("HISTORY_RETENTION_HOURS", 24)
        self.event_retention_hours = _int("EVENT_RETENTION_HOURS", 48)
        self.history_max_turns = _int("HISTORY_MAX_TURNS", 10)
        self.prompt_file = Path(
            _str("DIALOGUE_PROMPT_FILE", str(BASE_DIR / "prompts" / "dialogue.md"))
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings() -> None:
    """テストで環境変数を差し替えたときに呼ぶ。"""
    get_settings.cache_clear()
