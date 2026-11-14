"""本番の設定の確認（`python manage.py check --deploy` で実行される）。"""

from pathlib import Path

from django.conf import settings
from django.core.checks import Warning, register

from .admins import admin_emails_path


@register(deploy=True)
def check_admin_emails_file(app_configs, **kwargs):
    """管理者リストのファイルが、コードの外に置かれ、読める状態かを確認する。"""
    path = admin_emails_path()
    messages = []
    if path.is_relative_to(Path(settings.BASE_DIR)):
        messages.append(
            Warning(
                "管理者リストのファイルがコードのディレクトリの中にあります。",
                hint=f"ADMIN_EMAILS_FILE に {settings.BASE_DIR} の外の絶対パスを設定してください"
                "（デプロイでコードが置き換わると消えます）。",
                id="accounts.W001",
            )
        )
    if not path.is_file():
        messages.append(
            Warning(
                f"管理者リストのファイルが見つかりません: {path}",
                hint="このままでは管理者が1人もいない状態になります。",
                id="accounts.W002",
            )
        )
    return messages
