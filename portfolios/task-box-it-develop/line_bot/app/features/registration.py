"""ユーザー情報の登録。

入り口はLIFFとテキストの2つだが、検証と保存はこのモジュールに集約する。
`line_user_id` は、署名を検証したWebhookか、検証済みのIDトークンから渡された値のみを受け取る。
"""

import re

from sqlalchemy import select

from .. import messages as msg
from ..models import ContractStatus, User

HEADER = "【ユーザー情報の登録】"
NAME_LABEL = "名前"
EMAIL_LABEL = "メールアドレス"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]+$")
NAME_MAX = 50
EMAIL_MAX = 254


class ValidationError(Exception):
    pass


def matches(text: str) -> bool:
    return text.strip().startswith(HEADER)


def parse(text: str) -> tuple[str, str]:
    """テキストから名前とメールアドレスを取り出す。"""
    values: dict[str, str] = {}
    for line in text.strip().splitlines()[1:]:
        label, sep, value = line.partition(":")
        if not sep:
            label, sep, value = line.partition("：")
        if sep:
            values[label.strip()] = value.strip()
    if NAME_LABEL not in values or EMAIL_LABEL not in values:
        raise ValidationError("形式が違います。")
    return validate(values[NAME_LABEL], values[EMAIL_LABEL])


def validate(name: str, email: str) -> tuple[str, str]:
    name = (name or "").strip()
    email = (email or "").strip()
    if not name:
        raise ValidationError("お名前が入っていません。")
    if len(name) > NAME_MAX:
        raise ValidationError(f"お名前が長すぎます（{NAME_MAX}文字まで）。")
    if len(email) > EMAIL_MAX or not EMAIL_PATTERN.match(email):
        raise ValidationError("メールアドレスの形式が正しくありません。")
    return name, email


def register(session, line_user_id: str, name: str, email: str) -> User:
    """1アカウント1件で上書きする。契約状態は変えない。"""
    user = session.get(User, line_user_id)
    if user is None:
        user = User(line_user_id=line_user_id, contract_status=ContractStatus.NONE)
    user.name = name
    user.email = email
    session.add(user)
    session.flush()
    return user


def register_from_text(session, line_user_id: str, text: str) -> str:
    """テキストでの登録。返信の文面を返す。"""
    try:
        name, email = parse(text)
    except ValidationError as exc:
        return msg.format_error(str(exc))
    register(session, line_user_id, name, email)
    return msg.REGISTERED


def guide(session, line_user_id: str, liff_url: str) -> str:
    return msg.register_guide(liff_url)


def find(session, line_user_id: str) -> User | None:
    return session.scalar(select(User).where(User.line_user_id == line_user_id))
