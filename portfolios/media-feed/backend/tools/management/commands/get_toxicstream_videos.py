import hashlib
import re
import urllib.parse as up
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Content, Tag

BASE_URL = "https://toxicstream.com"
SITE_NAME = "toxicstream"
VIDEO_URL_PATTERN = re.compile(r"^https://toxicstream\.com/\d+/$")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


class Command(BaseCommand):
    help = "toxicstream.com の動画情報を取得してデータベースに保存する"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--url", help="取得対象のURL")
        group.add_argument("--tag", help="タグ名")
        parser.add_argument("--number", type=int, default=10, help="取得する動画数 (デフォルト: 10)")

    def handle(self, *args, **options):
        if options["tag"]:
            start_url = f"{BASE_URL}/tag/{options['tag']}/"
        elif options["url"]:
            start_url = options["url"]
        else:
            start_url = BASE_URL + "/"

        number = options["number"]
        self.stdout.write(f"URL取得中: {start_url}")
        video_urls = self._fetch_video_urls(start_url, number)
        self.stdout.write(f"{len(video_urls)} 件のURLを取得しました。\n")

        video_dir = Path(settings.MEDIA_ROOT) / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)

        for i, page_url in enumerate(video_urls, 1):
            self.stdout.write(f"[{i}/{len(video_urls)}] {page_url}")
            try:
                mp4_urls, meta = self._find_mp4_urls(page_url)
                if not mp4_urls:
                    self.stdout.write("  MP4 URLが見つかりませんでした。スキップ")
                    continue
                for mp4_url in mp4_urls:
                    filepath = self._download(mp4_url, page_url, video_dir)
                    if filepath:
                        self._save_to_db(filepath, mp4_url, meta, page_url)
            except Exception as e:
                self.stderr.write(f"  エラー: {e}")

    def _build_page_url(self, base: str, page: int) -> str:
        if page <= 1:
            return base.rstrip("/") + "/"
        return base.rstrip("/") + f"/page/{page}/"

    def _fetch_video_urls(self, start_url: str, number: int) -> list[str]:
        collected: list[str] = []
        seen: set[str] = set()
        page = 1
        while len(collected) < number:
            url = self._build_page_url(start_url, page)
            self.stdout.write(f"  ページ {page}: {url}")
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
            except requests.HTTPError as e:
                self.stderr.write(f"  取得失敗: {e}")
                break
            page_urls = [
                a["href"] if a["href"].startswith("http") else BASE_URL + a["href"]
                for a in soup.find_all("a", href=True)
                if VIDEO_URL_PATTERN.match(a["href"] if a["href"].startswith("http") else BASE_URL + a["href"])
            ]
            if not page_urls:
                break
            for u in page_urls:
                if u not in seen and len(collected) < number:
                    seen.add(u)
                    collected.append(u)
            page += 1
        return collected

    def _find_mp4_urls(self, page_url: str) -> tuple[list[str], dict]:
        resp = requests.get(page_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen: set[str] = set()
        mp4_urls: list[str] = []
        for video in soup.find_all("video"):
            for src_attr in [video.get("src", ""), *[s.get("src", "") for s in video.find_all("source")]]:
                if src_attr and ".mp4" in src_attr:
                    full = up.urljoin(page_url, src_attr)
                    if full not in seen:
                        seen.add(full)
                        mp4_urls.append(full)
        if not mp4_urls:
            for pat in [
                r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
                r'src\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
                r'"(https?://[^"]+\.mp4[^"]*)"',
            ]:
                for vurl in re.findall(pat, resp.text, re.IGNORECASE):
                    full = up.urljoin(page_url, vurl)
                    if full not in seen:
                        seen.add(full)
                        mp4_urls.append(full)

        meta = self._extract_meta(soup, page_url)
        return mp4_urls, meta

    def _extract_meta(self, soup: BeautifulSoup, page_url: str) -> dict:
        title_tag = soup.find("title")
        title = title_tag.text.strip() if title_tag else ""
        name_tag = soup.find(class_="name")
        user = name_tag.get_text(strip=True) if name_tag else SITE_NAME
        desc_tag = soup.select_one(".entry-content.cf")
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        tags = [t.get_text(strip=True) for t in soup.select("a.tag-link") if t.get_text(strip=True)]
        return {"title": title, "description": description, "user": user, "tags": tags}

    def _download(self, mp4_url: str, referer: str, output_dir: Path) -> str | None:
        filename = mp4_url.split("/")[-1].split("?")[0] or "video.mp4"
        filepath = output_dir / filename
        if filepath.exists():
            self.stdout.write(f"  既存ファイル: {filename}")
            return str(filepath)
        self.stdout.write(f"  ダウンロード: {filename}")
        try:
            with requests.get(mp4_url, headers={**HEADERS, "Referer": referer}, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        f.write(chunk)
            return str(filepath)
        except Exception as e:
            self.stderr.write(f"  ダウンロードエラー: {e}")
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
