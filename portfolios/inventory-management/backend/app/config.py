"""アプリケーションの設定（環境変数・.env から読み込む）。"""

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# 開発・テスト専用の秘密鍵。本番（APP_ENV=production）では使えない。
DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"  # noqa: S105
MIN_PRODUCTION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./inventory.db"
    jwt_secret: str = DEV_JWT_SECRET
    access_token_expire_minutes: int = 60
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("jwt_secret", mode="before")
    @classmethod
    def _empty_secret_is_unset(cls, value: object) -> object:
        # 空文字（.env.example のまま・compose で未指定）は未設定として扱う
        if isinstance(value, str) and not value.strip():
            return DEV_JWT_SECRET
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate_for_env(self) -> None:
        """本番環境で安全でない設定なら ValueError を送出する。"""
        if not self.is_production:
            return
        if self.jwt_secret == DEV_JWT_SECRET:
            raise ValueError("本番環境では JWT_SECRET を設定してください。")
        if len(self.jwt_secret) < MIN_PRODUCTION_SECRET_LENGTH:
            raise ValueError(
                f"本番環境の JWT_SECRET は {MIN_PRODUCTION_SECRET_LENGTH} 文字以上にしてください。"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
