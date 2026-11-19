"""Wikipedia のカテゴリーからコスプレイヤーの情報を収集する（CP-2）。

例: python manage.py fetch_cosplayers --limit 50
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from catalog.collector import runner
from catalog.collector.fetcher import Fetcher


class Command(BaseCommand):
    help = "コスプレイヤーの情報を収集して DB に取り込む"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, help="取り込む人数の上限")
        parser.add_argument("--force", action="store_true", help="取得済みの人物ページも取得し直す")

    def handle(self, *args, **options):
        if options["limit"] is not None and options["limit"] < 1:
            raise CommandError("--limit は1以上を指定してください")
        with runner.build_client() as client:
            fetcher = Fetcher(client, min_interval=settings.FETCH_MIN_INTERVAL)
            counts = runner.run_cosplayer_collection(
                fetcher, runner.WIKIPEDIA_CATEGORY_URL, options["limit"], options["force"]
            )
        self.stdout.write(" ".join(f"{k}={v}" for k, v in counts.items()))
        if counts["failed"] and not counts["pages"]:
            raise CommandError("カテゴリーページの取得に失敗しました")
