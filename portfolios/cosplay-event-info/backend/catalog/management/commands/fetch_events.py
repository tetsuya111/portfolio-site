"""対象サイトからイベントの予定を収集する（EV-2）。

例: python manage.py fetch_events --site cos-cam --force
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from catalog.collector import runner
from catalog.collector.fetcher import Fetcher
from catalog.collector.normalizer import get_normalizer
from catalog.collector.parsers import events


class Command(BaseCommand):
    help = "対象サイトからイベントの予定を収集して DB に取り込む"

    def add_arguments(self, parser):
        parser.add_argument(
            "--site",
            action="append",
            help=f"収集するサイト（複数指定可）。指定しなければ全サイト: {', '.join(events.SITES)}",
        )
        parser.add_argument("--force", action="store_true", help="取得済みのページも取得し直す")

    def handle(self, *args, **options):
        names = options["site"] or list(events.SITES)
        unknown = [n for n in names if n not in events.SITES]
        if unknown:
            raise CommandError(f"不明なサイト: {', '.join(unknown)}")

        with runner.build_client() as client:
            fetcher = Fetcher(client, min_interval=settings.FETCH_MIN_INTERVAL)
            results = runner.run_event_collection(
                fetcher,
                [events.SITES[n] for n in names],
                runner.CachedNormalizer(get_normalizer()),
                timezone.localdate(),
                force=options["force"],
            )

        for name, counts in results.items():
            summary = " ".join(f"{k}={v}" for k, v in counts.items())
            self.stdout.write(f"{name}: {summary}")
        if all(c["failed"] and not c["pages"] and not c["skipped"] for c in results.values()):
            raise CommandError("すべてのサイトで取得に失敗しました")
