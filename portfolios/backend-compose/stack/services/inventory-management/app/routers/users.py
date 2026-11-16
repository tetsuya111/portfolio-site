"""ユーザー API。"""

from fastapi import APIRouter
from sqlalchemy import select

from app.deps import AdminUser, CurrentUser, DbSession
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut, summary="ログインユーザー情報の取得")
def read_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("", response_model=list[UserOut], summary="ユーザー一覧（管理者のみ）")
def list_users(db: DbSession, _admin: AdminUser) -> list[UserOut]:
    users = db.scalars(select(User).order_by(User.id)).all()
    return [UserOut.model_validate(u) for u in users]
