"""
SeriesQueueItem作成バッチ

Usage:
  make_series_queue [--dry-run]

Options:
  --dry-run    実際には保存せず作成数だけ表示する
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "SeriesQueueItem を再構築する（既存データは全削除して再作成）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="実際には保存せず作成数だけ表示する",
        )

    def handle(self, *args, **options):
        from api.models import Series, SeriesQueueItem, Content, ContentDetail

        dry_run = options["dry_run"]
        items = []

        # ── Series → SeriesQueueItem ─────────────────────────
        series_list = list(Series.objects.all())
        self.stdout.write(f"シリーズ数: {len(series_list)}")
        for series in series_list:
            weight = max(1, int(series.weight))
            for _ in range(weight):
                items.append(SeriesQueueItem(series_id=series.series_id))
        self.stdout.write(f"  シリーズ由来アイテム数: {len(items)}")

        # ── シリーズなし Content → SeriesQueueItem ────────────
        standalone = Content.objects.filter(detail__series__isnull=True)
        standalone_count = standalone.count()
        self.stdout.write(f"シリーズなしコンテンツ数: {standalone_count}")
        for content in standalone.iterator():
            for _ in range(10):
                items.append(SeriesQueueItem(series_id=content.id))
        self.stdout.write(f"  合計アイテム数: {len(items)}")

        if dry_run:
            self.stdout.write("[DRY] 保存をスキップしました")
            return

        SeriesQueueItem.objects.all().delete()
        SeriesQueueItem.objects.bulk_create(items, batch_size=1000)
        self.stdout.write(f"完了: {SeriesQueueItem.objects.count()} 件作成")
