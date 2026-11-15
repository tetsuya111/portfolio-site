import hashlib
import re
import os
import uuid
from pathlib import Path
import time
import random

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
    help = "DMMの商品情報から画像を取得・ダウンロードしてDBに登録する"

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

        image_dir = Path(settings.MEDIA_ROOT) / "images"
        image_dir.mkdir(parents=True, exist_ok=True)

        for item in items:
            try:
                title = item.get("title", "")
                affiliate_url = item.get("affiliateURL", "")
                description = item.get("description", "")

                iteminfo = item.get("iteminfo", {})
                tag_names: list[str] = []
                for key in ("genre", "maker", "actress"):
                    for entry in iteminfo.get(key, []):
                        name = entry.get("name", "")
                        if name:
                            tag_names.append(name)

                self.stdout.write(f"商品: {title}")

                # 大きいサムネイル画像 (series なし)
                large_url = item.get("imageURL", {}).get("large", "")
                if large_url:
                    filepath = self._download(large_url, image_dir)
                    if filepath:
                        self._save_to_db(filepath, large_url, title, tag_names, None, None, affiliate_url, description)

                # サンプル画像 (同一商品は同一 series_id)
                sample_urls: list[str] = []
                sample_url_obj = item.get("sampleImageURL", {})
                if sample_url_obj:
                    images = sample_url_obj.get("sample_s", {}).get("image", [])
                    if isinstance(images, list):
                        sample_urls = images

                if sample_urls:
                    series_id = self._new_series_id()
                    for idx, img_url in enumerate(sample_urls):
                        img_url=re.sub("pics.dmm","awsimgsrc.dmm",img_url)
                        img_url=re.sub("/digital/video/([^/]+)/([^.-]+)-([0-9]+).([^/]+)",r"/pics_dig/digital/video/\1/\2jp-\3.\4",img_url)
                        sample_title = f"{title} - {idx}"
                        filepath=""
                        retly_n=5
                        for _ in range(retly_n):
                            filepath = self._download(img_url, image_dir)
                            if filepath:
                                break
                            time.sleep(0.7+random.randint(-3,3)*0.1)
                        if filepath:
                            self._save_to_db(filepath, img_url, sample_title, tag_names, series_id, idx, affiliate_url, description)

                self.stdout.write("")
            except Exception as e:
                self.stderr.write(f"処理エラー: {e}")
                continue

    def _new_series_id(self) -> str:
        existing = set(Series.objects.values_list("series_id", flat=True))
        while True:
            sid = uuid.uuid4().hex[:8]
            if sid not in existing:
                return sid

    def _download(self, url: str, output_dir: Path) -> str | None:
        filename = url.split("/")[-1].split("?")[0] or "image.jpg"
        filepath = output_dir / filename
        if filepath.exists():
            self.stdout.write(f"  既存ファイル: {filename}")
            return str(filepath)
        self.stdout.write(f"  ダウンロード: {filename}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
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
        series_id: str | None,
        series_number: int | None,
        source_url: str,
        description: str,
    ) -> None:
        content_id = hashlib.sha256(f"{path}{link}{title}".encode()).hexdigest()[:32]
        obj, created = Content.objects.get_or_create(
            id=content_id,
            defaults={
                "type": Content.TYPE_IMAGE,
                "title": title,
                "path": path,
                "link": link,
                "source_url": source_url,
                "user": SITE_NAME,
                "description": description,
            },
        )
        if created:
            if series_id is not None and series_number is not None:
                series_obj, _ = Series.objects.get_or_create(series_id=series_id)
                ContentDetail.objects.create(
                    content=obj,
                    series=series_obj,
                    series_number=series_number,
                )
            for name in tag_names:
                if name:
                    tag, _ = Tag.objects.get_or_create(name=name)
                    tag.contents.add(obj)
            self.stdout.write(f"  保存完了: {title}")
        else:
            self.stdout.write(f"  既存: {content_id}")
