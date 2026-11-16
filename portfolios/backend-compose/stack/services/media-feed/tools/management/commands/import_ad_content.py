import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from api.models import AdContent, AdContentTag

COL_HTML = "html"
COL_TAGS = "tags"
COL_WIDTH = "width"
COL_HEIGHT = "height"


class Command(BaseCommand):
    help = "CSVから広告コンテンツを一括登録する"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="インポートするCSVファイルのパス")
        parser.add_argument(
            "--clear",
            action="store_true",
            default=False,
            help="登録前に既存の広告コンテンツをすべて削除する",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            self.stderr.write(f"CSVファイルが見つかりません: {csv_path}")
            return

        if options["clear"]:
            count = AdContent.objects.count()
            AdContent.objects.all().delete()
            self.stdout.write(f"既存の広告コンテンツを削除しました ({count}件)")

        rows = []
        for enc in ["utf-8-sig", "utf-8", "cp932"]:
            try:
                with open(csv_path, encoding=enc, newline="") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                self.stderr.write(f"エンコーディング: {enc}, 件数: {len(rows)}")
                break
            except (UnicodeDecodeError, Exception):
                continue

        if not rows:
            self.stderr.write("CSVの読み込みに失敗しました")
            return

        ok = skip = error = 0
        for i, row in enumerate(rows, 1):
            html = row.get(COL_HTML, "").strip()
            if not html:
                self.stderr.write(f"[SKIP] 行{i}: htmlが空です")
                skip += 1
                continue

            tag_names = [
                t.strip() for t in row.get(COL_TAGS, "").split(",")
                if t.strip()
            ]

            def _parse_int(val):
                try:
                    return int(val.strip())
                except (ValueError, AttributeError):
                    return None

            width = _parse_int(row.get(COL_WIDTH, ""))
            height = _parse_int(row.get(COL_HEIGHT, ""))

            try:
                ad = AdContent.objects.create(html=html, width=width, height=height)
                for name in tag_names:
                    tag, _ = AdContentTag.objects.get_or_create(name=name[:100])
                    ad.tags.add(tag)
                self.stdout.write(f"[OK] 行{i}: tags={tag_names or '-'} width={width} height={height}")
                ok += 1
            except Exception as e:
                self.stderr.write(f"[ERROR] 行{i}: {e}")
                error += 1

        self.stdout.write(f"\n完了: {ok}件登録, {skip}件スキップ, {error}件エラー")
