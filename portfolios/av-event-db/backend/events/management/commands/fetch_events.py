"""対象サイトからイベントを取り込むバッチ（REQ-1）。"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError, CommandParser

from events.crawler.fetcher import PageFetcher
from events.crawler.importer import EventImporter, run_source
from events.crawler.sources import load_sources
from events.crawler.venues import build_default_resolver


def build_fetcher(retry_unparsed: bool = False) -> PageFetcher:
    return PageFetcher(retry_unparsed=retry_unparsed)


class Command(BaseCommand):
    help = "sources.json の対象サイトからイベントを取り込む"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--source", action="append", default=[], help="取り込むサイト名（複数指定可）"
        )
        parser.add_argument("--limit", type=int, default=None, help="サイトごとの最大処理件数")
        parser.add_argument("--sources-file", type=Path, default=None, help="抽出ルールのファイル")
        parser.add_argument(
            "--retry-unparsed",
            action="store_true",
            help="前回イベントを抽出できなかった詳細ページも取り直す（抽出ルールの修正後に使う）",
        )

    def handle(self, *args, **options) -> None:
        sources = load_sources(options["sources_file"])
        wanted = options["source"]
        if wanted:
            unknown = set(wanted) - {s.name for s in sources}
            if unknown:
                raise CommandError(f"未知のサイト名です: {', '.join(sorted(unknown))}")
            sources = [s for s in sources if s.name in wanted]

        importer = EventImporter(build_default_resolver())
        fetcher = build_fetcher(retry_unparsed=options["retry_unparsed"])
        try:
            for source in sources:
                stats = run_source(source, fetcher, importer, limit=options["limit"])
                self.stdout.write(
                    f"{source.name}: 作成 {stats.created} / 統合 {stats.merged} / "
                    f"スキップ {stats.skipped} / 失敗 {stats.failed}"
                )
        finally:
            fetcher.close()
