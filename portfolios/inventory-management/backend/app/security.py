"""パスワードのハッシュ化と JWT の発行・検証。"""

import os
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import Settings
from app.models import User

JWT_ALGORITHM = "HS256"
# bcrypt はパスワードの先頭72バイトしか使わないため、それを超える入力は照合で拒否する。
BCRYPT_MAX_BYTES = 72
# コスト（既定12）。テストでは環境変数 BCRYPT_ROUNDS で下げて高速化する。
BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", "12"))
# 本番で許すコストの下限（テスト用の低い値が本番に紛れ込むのを防ぐ）
MIN_PRODUCTION_BCRYPT_ROUNDS = 10


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode(
        "ascii"
    )


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
    except ValueError:
        return False


# ユーザーが存在しないときにも照合を行い、応答時間からユーザーの有無を推測されにくくする。
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def verify_dummy_password(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def create_access_token(user: User, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str, settings: Settings) -> dict:
    """署名・有効期限を検証してクレームを返す。不正なら jwt.PyJWTError を送出する。"""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat"]},
    )
