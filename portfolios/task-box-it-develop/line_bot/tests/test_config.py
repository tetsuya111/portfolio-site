"""設定の読み取り。`.env.example` をコピーしたままの状態でも動くこと。"""

from app.config import BASE_DIR, get_settings, reset_settings


def settings_with(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    reset_settings()
    return get_settings()


class TestEmptyValues:
    def test_empty_database_url_falls_back_to_sqlite(self, monkeypatch):
        # `.env` の `DATABASE_URL=`（空文字）を「未設定」として扱う
        settings = settings_with(monkeypatch, DATABASE_URL="")
        assert settings.database_url == f"sqlite:///{BASE_DIR / 'line_bot.sqlite3'}"

    def test_empty_redis_url_falls_back(self, monkeypatch):
        assert settings_with(monkeypatch, REDIS_URL="").redis_url == "redis://localhost:6379/0"

    def test_empty_llm_model_falls_back(self, monkeypatch):
        assert settings_with(monkeypatch, LLM_MODEL="  ").llm_model == "claude-sonnet-5"

    def test_surrounding_spaces_are_removed(self, monkeypatch):
        # トークンを貼り付けたときの余分な空白で通信が壊れないようにする
        settings = settings_with(monkeypatch, LINE_CHANNEL_ACCESS_TOKEN="  abc123  ")
        assert settings.channel_access_token == "abc123"
