"""
Usage:
  get_dmm_videos [-k <keyword>] [-s <site>] [-p <params>] [-n <number>] [--of <offset>]
"""
import hashlib
import os
import re
import uuid
from pathlib import Path
import asyncio

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Content, ContentDetail, Series, Tag

DMM_API_BASE = "https://api.dmm.com/affiliate/v3/ItemList"
SITE_NAME = "DMM"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


class Command(BaseCommand):
    help = "DMMの商品情報から動画を取得・ダウンロードしてDBに登録する"

    def add_arguments(self, parser):
        parser.add_argument("-k", "--keyword", default="", help="検索キーワード")
        parser.add_argument("-s", "--site", default="FANZA", help="検索対象のサイト (default: FANZA)")
        parser.add_argument("-p", "--params", default="", help='追加パラメータ "<key>:<value>,..." 形式')
        parser.add_argument("-n", "--number", type=int, default=20, help="取得する商品情報の数 (default: 20)")
        parser.add_argument("--of", dest="offset", type=int, default=1, help="オフセット (default: 1)")

    def handle(self, *args, **options):
        api_id = os.environ.get("DMM_API_ID", "")
        affiliate_id = os.environ.get("DMM_AFFILIATE_ID", "")
        if not api_id or not affiliate_id:
            self.stderr.write("エラー: 環境変数 DMM_API_ID と DMM_AFFILIATE_ID を設定してください")
            return

        keyword = options["keyword"]
        site = options["site"]
        number = options["number"]
        offset = options["offset"]

        api_params: dict = {
            "api_id": api_id,
            "affiliate_id": affiliate_id,
            "site": site,
            "hits": min(number, 100),
            "offset": offset,
            "output": "json",
        }
        if keyword:
            api_params["keyword"] = keyword
        if options["params"]:
            for pair in options["params"].split(","):
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    api_params[k.strip()] = v.strip()

        self.stdout.write(
            f"DMM API 呼び出し: site={site}, keyword={keyword or '(なし)'}, hits={number}, offset={offset}"
        )
        try:
            resp = requests.get(DMM_API_BASE, params=api_params, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            self.stderr.write(f"API呼び出しエラー: {e}")
            return

        data = resp.json()
        result = data.get("result", {})
        if result.get("status") != 200:
            self.stderr.write(f"APIエラー: {result}")
            return

        items = result.get("items", [])
        if not items:
            self.stdout.write("商品が見つかりませんでした")
            return

        self.stdout.write(f"{len(items)} 件の商品を取得しました\n")

        video_dir = Path(settings.MEDIA_ROOT) / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)

        for item in items:
            title = item.get("title", "")
            affiliate_url = item.get("affiliateURL", "")
            print("affiliate_url", affiliate_url)
            description = item.get("description", "")
            if Content.objects.filter(source_url=affiliate_url, type=Content.TYPE_VIDEO).exists():
                self.stderr.write("その動画はすでに保存されています")
                continue

            iteminfo = item.get("iteminfo", {})
            tag_names: list[str] = []
            for key in ("genre", "maker", "actress"):
                for entry in iteminfo.get(key, []):
                    name = entry.get("name", "")
                    if name:
                        tag_names.append(name)

            self.stdout.write(f"商品: {title}")

            video_url=""
            # 商品ページからMP4を抽出 (pyppeteer)
            url = item.get("URL", "")
            if url:
                video_url = asyncio.run(self._extract_mp4_from_page(url))

            if not video_url:
                self.stdout.write(f"  動画URLが見つかりませんでした: {title}")
                continue

            # flash → mp4 URL変換
            if video_url.endswith(".flv") or video_url.endswith(".swf"):
                video_url = re.sub(r'\.(flv|swf)$', '.mp4', video_url)
            print("video_url",video_url)
            filepath = self._download(video_url, video_dir)
            if filepath:
                self._save_to_db(filepath, video_url, title, tag_names, affiliate_url, description)

            self.stdout.write("")

    async def _extract_mp4_from_page(self, url: str) -> str:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.stderr.write("  playwrightがインストールされていません: pip install playwright && python -m playwright install chromium")
            return ""
        try:
            mp4_urls: list[str] = []
            async with async_playwright() as pw:
                headless=True
                #headless=False
                browser = await pw.chromium.launch(headless=headless,args=["--no-sandbox"])
                context = await browser.new_context(user_agent=HEADERS["User-Agent"])
                page = await context.new_page()

                def on_request(req):
                    req_url = req.url
                    if ".mp4" in req_url:
                        mp4_urls.append(req_url)

                page.on("request", on_request)
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                try:
                    btn = page.locator(".css-1971p6n div", has_text="はい")
                    await btn.first.click(timeout=5000)
                except Exception:
                    pass
                await page.wait_for_timeout(5000)
                content = await page.content()
                await browser.close()

            # HTMLからmp4リンクを抽出
            mp4_in_html = re.findall(r'https?://[^\s\'"<>]+\.mp4[^\s\'"<>]*', content)
            print("mp4_in_html",mp4_in_html,url)
            mp4_urls.extend(mp4_in_html)

            if mp4_urls:
                return mp4_urls[0]
        except Exception as e:
            self.stderr.write(f"  playwrightエラー: {e}")
        return ""

    def _new_series_id(self) -> str:
        existing = set(Series.objects.values_list("series_id", flat=True))
        while True:
            sid = uuid.uuid4().hex[:8]
            if sid not in existing:
                return sid

    def _download(self, url: str, output_dir: Path) -> str | None:
        filename = url.split("/")[-1].split("?")[0] or "video.mp4"
        if not filename.endswith(".mp4"):
            filename += ".mp4"
        filepath = output_dir / filename
        if filepath.exists():
            self.stdout.write(f"  既存ファイル: {filename}")
            return str(filepath)
        self.stdout.write(f"  ダウンロード: {filename}")
        try:
            with requests.get(url, headers=HEADERS, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        f.write(chunk)
            return str(filepath)
        except Exception as e:
            self.stderr.write(f"  ダウンロードエラー: {e}")
            return None

    def _save_to_db(
        self,
        path: str,
        link: str,
        title: str,
        tag_names: list[str],
        source_url: str,
        description: str,
    ) -> None:
        content_id = hashlib.sha256(f"{path}{link}{title}".encode()).hexdigest()[:32]
        obj, created = Content.objects.get_or_create(
            id=content_id,
            defaults={
                "type": Content.TYPE_VIDEO,
                "title": title,
                "path": path,
                "link": link,
                "source_url": source_url,
                "user": SITE_NAME,
                "description": description,
            },
        )
        if created:
            for name in tag_names:
                if name:
                    tag, _ = Tag.objects.get_or_create(name=name)
                    tag.contents.add(obj)
            self.stdout.write(f"  保存完了: {title}")
        else:
            self.stdout.write(f"  既存: {content_id}")
