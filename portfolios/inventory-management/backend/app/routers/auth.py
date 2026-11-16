"""認証 API（ログイン・ユーザー登録）。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import AppSettings, DbSession
from app.models import User
from app.schemas import Token
from app.security import create_access_token, verify_dummy_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_ERROR = "ユーザー名またはパスワードが正しくありません。"


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        verify_dummy_password(password)
        return None
    if not verify_password(password, user.password_hash) or not user.is_active:
        return None
    return user


@router.post("/login", response_model=Token, summary="ログイン（JWT の発行）")
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
    settings: AppSettings,
) -> Token:
    user = authenticate(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=LOGIN_ERROR,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=create_access_token(user, settings),
        expires_in=settings.access_token_expire_minutes * 60,
    )
