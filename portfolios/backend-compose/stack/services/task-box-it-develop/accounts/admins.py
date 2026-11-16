"""管理者の判定。

管理者はGoogleアカウントのメールアドレスで指定し、その一覧はコードの外のテキストファイルに置く
（`ADMIN_EMAILS_FILE`）。1行1メールアドレスで、前後の空白と大文字・小文字の違いは無視し、空行と
`#` で始まる行は読み飛ばす。

ファイルが読めない場合は「管理者が1人もいない」として扱い、例外にしない（依頼者の利用は止めない）。
認可そのものは従来どおり User.role で行い、このモジュールはログイン時にその値を同期する。
ファイルの配置とパーミッションは docs/backend.md を参照。
"""

import logging
from pathlib import Path

from django.conf import settings

from .models import User

logger = logging.getLogger(__name__)

# {"key": (ファイルの状態, メールアドレスの集合)}。ファイルが更新されたときだけ読み直す
_cache = {}


def admin_emails_path():
    """設定されたパス。相対パスは実行時のカレントディレクトリに依存させない。"""
    path = Path(settings.ADMIN_EMAILS_FILE)
    return path if path.is_absolute() else Path(settings.BASE_DIR) / path


def reset_cache():
    _cache.clear()


def _parse(text):
    emails = set()
    for line in text.splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        emails.add(value.lower())
    return frozenset(emails)


def load_admin_emails():
    path = admin_emails_path()
    try:
        stat = path.stat()
        state = (str(path), stat.st_mtime_ns, stat.st_size)
        cached = _cache.get("key")
        if cached is not None and cached[0] == state:
            return cached[1]
        emails = _parse(path.read_text(encoding="utf-8"))
    except OSError as exc:
        # メールアドレスはログに出さない。出すのは件数と、読めなかった事実だけ
        if _cache.get("warned") != str(path):
            logger.warning("管理者リストのファイルを読み込めません（管理者なしとして扱います）: %s", exc)
            _cache["warned"] = str(path)
        _cache.pop("key", None)
        return frozenset()
    _cache["key"] = (state, emails)
    _cache.pop("warned", None)
    logger.info("管理者リストを読み込みました（%d件）", len(emails))
    return emails


def is_admin_email(email):
    return bool(email) and email.strip().lower() in load_admin_emails()


def sync_user_role(user, save=True):
    """ファイルの内容をユーザーの権限に反映する。変化がなければ保存しない。"""
    is_admin = is_admin_email(user.email)
    role = User.Role.ADMIN if is_admin else User.Role.GENERAL
    if user.role == role and user.is_staff == is_admin and user.is_superuser == is_admin:
        return False
    user.role = role
    # Djangoの管理サイト（ロールプロンプト・テンプレの編集）にも入れるようにする
    user.is_staff = is_admin
    user.is_superuser = is_admin
    if save and user.pk:
        user.save(update_fields=["role", "is_staff", "is_superuser"])
    return True
