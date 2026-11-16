"""ユーザーの作成（API と CLI で共用）。"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserCreate
from app.security import hash_password


class UsernameTaken(Exception):
    pass


def create_user(db: Session, data: UserCreate) -> User:
    if db.scalar(select(User.id).where(User.username == data.username)) is not None:
        raise UsernameTaken(data.username)
    user = User(username=data.username, password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # 同時に同じ名前で登録された場合
        db.rollback()
        raise UsernameTaken(data.username) from None
    return user
