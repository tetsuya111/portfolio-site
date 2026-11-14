"""
xvideosから動画を取得・ダウンロードしてDBに登録する

Usage:
    get_xvideos [(-k <keyword>)] [(-n <number>)]
    get_xvideos list <list_url>  [(-n <number>)]

Options:
    -k <keyword>    検索キーワード [default: ""]
    -n <number>     取得する動画数 [default: 10]
    list_url        動画一覧ページのURL
"""
import hashlib
import re
import subprocess
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Content, Tag

BASE_URL = "https://www.xvideos.com"
SITE_NAME = "xvideos"
VIDEO_PAGE_RE = re.compile(r"/video.[^\"]+")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

MP4_PATTERNS = [
    re.compile(r"html5player\.setVideoUrlHigh\('([^']+)'\)"),
    re.compile(r"html5player\.setVideoUrlLow\('([^']+)'\)"),
    re.compile(r"setVideoHLS\('([^']+)'\)"),
    re.compile(r'"videoUrl"\s*:\s*"([^"]+\.mp4[^"]*)"'),
    re.compile(r"'(https?://[^']+\.mp4[^']*)'"),
]


class Command(BaseCommand):
    help = "xvideosから動画を取得・ダウンロードしてDBに登録する"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="subcommand")

        # list モード
        list_parser = subparsers.add_parser("list", help="動画一覧ページから取得")
        list_parser.add_argument("list_url", help="動画一覧ページのURL")
        list_parser.add_argument("-n", type=int, default=10, dest="number", help="取得する動画数 (default: 10)")

        # キーワードモード（デフォルト）
        parser.add_argument("-k", "--keyword", default="", dest="keyword", help="検索キーワード")
        parser.add_argument("-n", type=int, default=10, dest="number", help="取得する動画数 (default: 10)")

    def handle(self, *args, **options):
        number = options["number"]
        video_dir = Path(settings.MEDIA_ROOT) / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)

        if options.get("subcommand") == "list":
            list_url = options["list_url"]
            self.stdout.write(f"一覧ページから取得: {list_url}")
            video_urls = self._collect_video_urls(list_url, number)
        else:
            keyword = options.get("keyword", "")
            if keyword:
                list_url = f"{BASE_URL}/?k={requests.utils.quote(keyword)}"
                self.stdout.write(f"キーワード検索: {keyword}")
            else:
                list_url = BASE_URL + "/"
                self.stdout.write("トップページから取得")
            video_urls = self._collect_video_urls(list_url, number)

        self.stdout.write(f"{len(video_urls)} 件の動画ページを取得しました\n")

        for i, video_url in enumerate(video_urls, 1):
            video_url = BASE_URL + video_url if video_url.startswith("/") else video_url
            self.stdout.write(f"[{i}/{len(video_urls)}] {video_url}")
            try:
                meta = self._fetch_content_info(video_url)
                if not meta:
                    self.stdout.write("  コンテンツ情報を取得できませんでした。スキップ")
                    continue
                mp4_url = meta.get("link", "")
                if not mp4_url:
                    self.stdout.write("  MP4 URLが見つかりませんでした。スキップ")
                    continue
                filepath = self._download(video_url, mp4_url, video_dir)
                if filepath:
                    meta["path"] = filepath
                    self._save_to_db(meta)
            except Exception as e:
                self.stderr.write(f"  エラー: {e}")

    def _collect_video_urls(self, start_url: str, number: int) -> list[str]:
        collected: list[str] = []
        seen: set[str] = set()
        page = 0

        while len(collected) < number:
            if page == 0:
                url = start_url
            else:
                # xvideos の検索ページネーション: &p=<page>
                sep = "&" if "?" in start_url else "?"
                url = f"{start_url}{sep}p={page}"

            self.stdout.write(f"  ページ取得: {url}")
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
                resp.raise_for_status()
            except Exception as e:
                self.stderr.write(f"  取得失敗: {e}")
                break

            found = VIDEO_PAGE_RE.findall(resp.text)
            new_found = [u for u in found if u not in seen]
            if not new_found:
                break

            for u in new_found:
                if len(collected) >= number:
                    break
                seen.add(u)
                collected.append(u)

            page += 1
        print("collected:", collected)
        return collected[:number]

    def _fetch_content_info(self, video_page_url: str) -> dict | None:
        try:
            resp = requests.get(video_page_url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            self.stderr.write(f"  ページ取得エラー: {e}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        html = resp.text

        # タイトル
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # MP4 URL 抽出
        mp4_url = ""
        for pat in MP4_PATTERNS:
            m = pat.search(html)
            if m:
                mp4_url = m.group(1)
                break

        # タグ (.video-tags-list li)
        tags = [
            li.get_text(strip=True)
            for li in soup.select(".video-tags-list li")
            if li.get_text(strip=True)
        ]

        return {
            "type": Content.TYPE_VIDEO,
            "title": title,
            "path": "",
            "link": mp4_url,
            "source_url": video_page_url,
            "user": SITE_NAME,
            "description": title,
            "tags": tags,
        }

    def _download(self, page_url: str, mp4_url: str, output_dir: Path) -> str | None:
        output_template = str(output_dir / "%(title)s.%(ext)s")
        # yt-dlp でページURLからダウンロード（mp4_url が HLS の場合も対応）
        cmd = [
            "yt-dlp",
            "--output", output_template,
            "--print", "after_move:filepath",
            "--no-warnings",
            page_url,
        ]
        self.stdout.write(f"  ダウンロード: {page_url}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            filepath = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None
            return filepath
        except subprocess.CalledProcessError as e:
            self.stderr.write(f"  ダウンロードエラー: {e.stderr[:200]}")
            return None

    def _save_to_db(self, meta: dict) -> None:
        path = meta.get("path", "")
        link = meta.get("link", "")
        title = meta.get("title", "")

        content_id = hashlib.sha256(f"{path}{link}{title}".encode()).hexdigest()[:32]
        obj, created = Content.objects.get_or_create(
            id=content_id,
            defaults={
                "type": Content.TYPE_VIDEO,
                "title": title,
                "path": path,
                "link": link,
                "source_url": meta.get("source_url", ""),
                "user": meta.get("user", SITE_NAME),
                "description": meta.get("description", ""),
            },
        )
        if created:
            for tag_name in meta.get("tags", []):
                if tag_name:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    tag.contents.add(obj)
            self.stdout.write(f"  保存完了: {obj.id}")
        else:
            self.stdout.write(f"  既存: {obj.id}")
