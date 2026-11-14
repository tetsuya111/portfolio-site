import asyncio
import hashlib
import re
import urllib.parse as up
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from pyppeteer import launch

from api.models import Content, Tag

BASE_URL = "https://hime-channel.com"
CHROME_PATH = r"C:\Users\USER\bin\chrome-win\chrome.exe"
SITE_NAME = "hime-channel"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


class Command(BaseCommand):
    help = "hime-channel.com の動画情報を取得してデータベースに保存する"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--url", help="取得対象のURL")
        group.add_argument("--tag", help="タグ名")
        parser.add_argument("--number", type=int, default=10, help="取得する動画数 (デフォルト: 10)")

    def handle(self, *args, **options):
        if options["tag"]:
            start_url = f"{BASE_URL}/tag/{options['tag']}"
        elif options["url"]:
            start_url = options["url"]
        else:
            start_url = BASE_URL

        asyncio.run(self._run(start_url, options["number"]))

    async def _run(self, start_url: str, number: int) -> None:
        self.stdout.write(f"URL取得中: {start_url}")
        video_urls = await self._extract_video_urls(start_url, number)
        self.stdout.write(f"{len(video_urls)} 件のURLを取得しました。\n")

        video_dir = Path(settings.MEDIA_ROOT) / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)

        for i, page_url in enumerate(video_urls, 1):
            self.stdout.write(f"[{i}/{len(video_urls)}] {page_url}")
            try:
                mp4_urls, meta = await self._find_mp4_url(page_url)
                if not mp4_urls:
                    self.stdout.write("  MP4 URLが見つかりませんでした。スキップ")
                    continue
                for mp4_url in mp4_urls:
                    filepath = self._download(mp4_url, page_url, video_dir)
                    if filepath:
                        self._save_to_db(filepath, mp4_url, meta, page_url)
            except Exception as e:
                self.stderr.write(f"  エラー: {e}")

    async def _extract_video_urls(self, start_url: str, number: int) -> list[str]:
        browser = await launch(
            headless=True,
            executablePath=CHROME_PATH,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = await browser.newPage()
        await page.goto(start_url, {"waitUntil": "networkidle2", "timeout": 60000})

        seen: set[str] = set()
        urls: list[str] = []
        no_new_rounds = 0

        while len(urls) < number:
            content = await page.content()
            for u in re.findall(r'href=["\']([^"\']*\/video\/[^"\']*)["\']', content):
                if not u.startswith("http"):
                    u = BASE_URL + u
                if u not in seen:
                    seen.add(u)
                    urls.append(u)
            if len(urls) >= number:
                break
            prev_len = len(seen)
            if len(seen) == prev_len:
                no_new_rounds += 1
                if no_new_rounds >= 3:
                    break
            else:
                no_new_rounds = 0
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

        await browser.close()
        return urls[:number]

    async def _find_mp4_url(self, page_url: str) -> tuple[list[str], dict]:
        browser = await launch(
            headless=True,
            executablePath=CHROME_PATH,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = await browser.newPage()
        await page.goto(page_url, {"waitUntil": "networkidle2", "timeout": 60000})
        content = await page.content()

        patterns = [
            r'<source[^>]+src=["\']([^"\']+\.mp4[^"\']*)["\']',
            r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            r'src\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            r'"(https?://[^"]+\.mp4[^"]*)"',
        ]
        seen: set[str] = set()
        mp4_urls: list[str] = []
        for pat in patterns:
            for vurl in re.findall(pat, content, re.IGNORECASE):
                vurl = up.urljoin(page.url, vurl)
                if vurl not in seen:
                    seen.add(vurl)
                    mp4_urls.append(vurl)

        meta = self._extract_meta(content)
        await browser.close()
        return mp4_urls, meta

    def _extract_meta(self, content: str) -> dict:
        def find(pattern):
            m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            return m.group(1).strip() if m else None

        title = (
            find(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']')
            or find(r'<title[^>]*>([^<]+)</title>')
        )
        user = find(r'class=["\']name["\'][^>]*>\s*([^<]+?)\s*<')
        description = find(r'class=["\']message["\'][^>]*>\s*(.*?)\s*</')
        tag_area = find(r'class=["\']tag-area["\'][^>]*>(.*?)</div>')
        tags = [t.strip() for t in re.findall(r'<a[^>]*>([^<]+)</a>', tag_area or "") if t.strip()]
        return {"title": title or "", "description": description or "", "user": user or SITE_NAME, "tags": tags}

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
