from django.core.management.base import BaseCommand

from accounts.admins import admin_emails_path, load_admin_emails, sync_user_role
from accounts.models import User


class Command(BaseCommand):
    help = (
        "管理者リストのファイル（ADMIN_EMAILS_FILE）の内容を、既存のすべてのユーザーの権限に反映する。"
        "通常はログイン時に反映されるため、ファイルによる指定へ切り替えるときや、"
        "ログインを待たずに反映したいときに使う"
    )

    def handle(self, *args, **options):
        emails = load_admin_emails()
        changed = 0
        for user in User.objects.all():
            if sync_user_role(user):
                changed += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"{admin_emails_path()}: 管理者 {len(emails)}件 / 権限を更新したユーザー {changed}人"
            )
        )
        if not emails:
            self.stdout.write(self.style.WARNING("管理者が1人もいない状態です"))
