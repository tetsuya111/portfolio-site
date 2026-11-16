from django.conf import settings
from django.core.management.base import BaseCommand

from chat.retention import purge_expired_conversations


class Command(BaseCommand):
    help = (
        "保持期間（CONVERSATION_RETENTION_DAYS 日）を過ぎた対話履歴を消す。"
        "1日1回の定期実行を想定している"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="消さずに対象の件数だけを表示する"
        )

    def handle(self, *args, dry_run, **options):
        result = purge_expired_conversations(dry_run=dry_run)
        self.stdout.write(
            self.style.SUCCESS(
                f"保持期間 {settings.CONVERSATION_RETENTION_DAYS}日"
                f"（{result['threshold']:%Y-%m-%d %H:%M} より前が対象）: "
                f"対話 {result['conversations']}件 / メッセージ {result['messages']}件"
                + ("を消しました" if not dry_run else "が対象です（dry-run のため消していません）")
            )
        )
