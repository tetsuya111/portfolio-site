"""
ブログパーツHTMLをbackend APIから取得してファイルに保存するバッチ

Usage:
  make_blog_parts [-o <output>] [--cols N] [--rows N] [-k <keyword>]
                  [--color <color>] [--font-color <color>]
                  [--tile-size N] [--api-url <url>] [--site-url <url>]
"""
import requests
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "blog-parts APIからHTMLを取得してファイルに保存する"

    def add_arguments(self, parser):
        parser.add_argument(
            "-o", "--output",
            default="blog_parts.html",
            help="出力ファイルパス (default: blog_parts.html)",
        )
        parser.add_argument("--cols", type=int, default=3, help="列数 (default: 3)")
        parser.add_argument("--rows", type=int, default=3, help="行数 (default: 3)")
        parser.add_argument("-k", "--keyword", default="", help="キーワードフィルタ")
        parser.add_argument(
            "--color", default="#1a1a2e", help="タイトルバーの背景色 (default: #1a1a2e)"
        )
        parser.add_argument(
            "--font-color",
            default="#ffffff",
            dest="font_color",
            help="タイトルバーの文字色 (default: #ffffff)",
        )
        parser.add_argument(
            "--tile-size",
            type=int,
            default=150,
            dest="tile_size",
            help="タイルの一辺のサイズ (px, default: 150)",
        )
        parser.add_argument(
            "--api-url",
            default="http://localhost:8000",
            dest="api_url",
            help="APIのベースURL (default: http://localhost:8000)",
        )
        parser.add_argument(
            "--site-url",
            default="http://localhost:3000",
            dest="site_url",
            help="フロントエンドのベースURL。タイルのリンク先に使用 (default: http://localhost:3000)",
        )

    def handle(self, *args, **options):
        api_url = options["api_url"].rstrip("/")
        params = {
            "cols": options["cols"],
            "rows": options["rows"],
            "color": options["color"],
            "font_color": options["font_color"],
            "tile_size": options["tile_size"],
            "site_url": options["site_url"],
        }
        if options["keyword"]:
            params["keyword"] = options["keyword"]

        endpoint = f"{api_url}/api/blog-parts/"
        self.stdout.write(f"APIリクエスト: {endpoint}")
        self.stdout.write(f"パラメータ: {params}")

        try:
            resp = requests.get(endpoint, params=params, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            self.stderr.write(f"APIエラー: {e}")
            return

        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(resp.text, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"保存完了: {output.resolve()}"))
