import hashlib
import re
import subprocess
import urllib.parse as up
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Content, Tag

BASE_URL = "https://zettai-ero.com"
SITE_NAME = "zettai-ero"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


class Command(BaseCommand):
    help = "zettai-ero.com の動画情報を取得してデータベースに保存する"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--url", help="取得対象のURL")
        group.add_argument("--tag", help="タグ名")
        parser.add_argument("--number", type=int, default=10, help="取得する動画数 (デフォルト: 10)")

    def handle(self, *args, **options):
        if options["tag"]:
            start_url = f"{BASE_URL}/?tag={up.quote(options['tag'])}"
        elif options["url"]:
            start_url = options["url"]
        else:
            start_url = BASE_URL

        number = options["number"]
        self.stdout.write(f"URL取得中: {start_url}")
        video_page_urls = self._extract_video_page_urls(start_url, number)
        self.stdout.write(f"{len(video_page_urls)} 件のURLを取得しました。\n")

        video_dir = Path(settings.MEDIA_ROOT) / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)

        for i, page_url in enumerate(video_page_urls, 1):
            self.stdout.write(f"[{i}/{len(video_page_urls)}] {page_url}")
            try:
                meta = self._extract_meta(page_url)
                tm_urls = self._get_tokyomotion_urls(page_url)
                if not tm_urls:
                    self.stdout.write("  tokyomotion URLが見つかりませんでした。スキップ")
                    continue
                for tm_url in tm_urls:
                    filepath = self._download(tm_url, video_dir)
                    if filepath:
                        self._save_to_db(filepath, tm_url, meta, page_url)
            except Exception as e:
                self.stderr.write(f"  エラー: {e}")

    def _extract_video_page_urls(self, start_url: str, number: int) -> list[str]:
        collected: list[str] = []
        seen: set[str] = set()
        page_num = 1
        while len(collected) < number:
            current_url = start_url if page_num == 1 else self._next_page_url(start_url, page_num)
            self.stdout.write(f"  ページ取得中: {current_url}")
            try:
                resp = requests.get(current_url, headers=HEADERS, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
            except Exception as e:
                self.stderr.write(f"  取得失敗: {e}")
                break
            found = False
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if re.search(r"\?p=\d+", href):
                    full = up.urljoin(BASE_URL, href)
                    if full not in seen:
                        seen.add(full)
                        collected.append(full)
                        found = True
                    if len(collected) >= number:
                        break
            if not found:
                break
            page_num += 1
        return collected[:number]

    def _next_page_url(self, base_url: str, page_num: int) -> str:
        parsed = up.urlparse(base_url)
        params = dict(up.parse_qsl(parsed.query))
        params["paged"] = str(page_num)
        return up.urlunparse(parsed._replace(query=up.urlencode(params)))

    def _get_tokyomotion_urls(self, page_url: str) -> list[str]:
        resp = requests.get(page_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        seen: set[str] = set()
        urls: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "tokyomotion.net" in href and href not in seen:
                seen.add(href)
                urls.append(href)
        for iframe in soup.find_all("iframe", src=True):
            src = iframe["src"]
            if "tokyomotion.net" in src and src not in seen:
                seen.add(src)
                urls.append(src)
        return urls

    def _extract_meta(self, page_url: str) -> dict:
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            title_tag = soup.find("title")
            title = title_tag.text.strip() if title_tag else ""
            name_tag = soup.find(class_="name")
            user = name_tag.get_text(strip=True) if name_tag else SITE_NAME
            desc_tag = soup.select_one('meta[name="description"]')
            description = desc_tag.get("content", "") if desc_tag else ""
            tags = [t.get_text(strip=True) for t in soup.select(".post_tag li") if t.get_text(strip=True)]
            return {"title": title, "user": user, "description": description, "tags": tags}
        except Exception as e:
            self.stderr.write(f"  メタ情報取得エラー: {e}")
            return {"title": "", "user": SITE_NAME, "description": "", "tags": []}

    def _download(self, tm_url: str, output_dir: Path) -> str | None:
        output_template = str(output_dir / "%(title)s.%(ext)s")
        cmd = [
            "yt-dlp",
            "--output", output_template,
            "--print", "after_move:filepath",
            tm_url,
        ]
        self.stdout.write(f"  ダウンロード: {tm_url}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            filepath = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None
            return filepath
        except subprocess.CalledProcessError as e:
            self.stderr.write(f"  ダウンロードエラー: {e.stderr}")
            return None

    def _save_to_db(self, path: str, link: str, meta: dict, source_url: str = "") -> None:
        title = meta.get("title") or ""
        content_id = hashlib.sha256(f"{path}{link}{title}".encode()).hexdigest()[:32]
        obj, created = Content.objects.get_or_create(
            id=content_id,
            defaults={
                "type": Content.TYPE_VIDEO,
                "title": title,
                "path": path,
                "link": link,
                "source_url": source_url,
                "user": meta.get("user") or SITE_NAME,
                "description": meta.get("description") or "",
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
