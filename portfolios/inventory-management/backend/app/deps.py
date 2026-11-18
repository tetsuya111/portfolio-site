"""ルーターで共通に使う依存関係（設定・ログインユーザー・権限）。"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.models import ROLE_ADMIN, ROLE_VISITOR, User
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="認証が必要です。ログインし直してください。",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]


def get_current_user(
    db: DbSession,
    settings: AppSettings,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if not token:
        raise CREDENTIALS_ERROR
    try:
        claims = decode_token(token, settings)
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise CREDENTIALS_ERROR from None
    user = db.get(User, user_id)
    # 権限は DB の値を正とする（トークン発行後の無効化・権限変更を反映する）。
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="管理者のみ操作できます。"
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]

VISITOR_FORBIDDEN = "閲覧者は操作できません"


def require_no_visitor(user: CurrentUser) -> User:
    """閲覧者を拒否する。データを作成・更新するエンドポイントには必ず付けること。"""
    if user.role == ROLE_VISITOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=VISITOR_FORBIDDEN)
    return user


EditorUser = Annotated[User, Depends(require_no_visitor)]
