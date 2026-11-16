"""ユーザー API。"""

from fastapi import APIRouter

from app.deps import CurrentUser
from app.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut, summary="ログインユーザー情報の取得")
def read_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
