"""
Seriesの重み計算バッチ

Usage:
  calc_series_weight [--dry-run]

Options:
  --dry-run    実際には保存せず計算結果だけ表示する
"""
import math

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Series.weight を再計算してデータベースを更新する"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="実際には保存せず計算結果だけ表示する",
        )

    def handle(self, *args, **options):
        from api.models import Series, ContentDetail

        dry_run = options["dry_run"]
        series_list = list(Series.objects.all())
        self.stdout.write(f"対象シリーズ数: {len(series_list)}")

        for series in series_list:
            series_count = ContentDetail.objects.filter(series=series).count()
            if series_count < 10:
                weight = 10.0
            else:
                weight = 10 * math.log10(series_count)

            self.stdout.write(
                f"  {series.series_id[:40]:<40} count={series_count:>5}  weight={weight:.2f}"
                + (" [DRY]" if dry_run else "")
            )
            if not dry_run:
                series.weight = weight
                series.save(update_fields=["weight"])

        self.stdout.write("完了")
