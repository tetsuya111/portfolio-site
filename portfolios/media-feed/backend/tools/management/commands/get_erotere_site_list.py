"""
eroterest.net のサイト一覧から登録サイトを取得してCSV出力する

Usage:
    get_erotere_site_list

Options:
    (なし)
"""
import csv
import sys
import time

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

BASE_URL = "https://movie.eroterest.net"
SITE_LIST_URL = f"{BASE_URL}/site/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


class Command(BaseCommand):
    help = "eroterest.net のサイト一覧から登録サイトを取得してCSV出力する"

    def handle(self, *args, **options):
        writer = csv.writer(sys.stdout)
        writer.writerow(["タイトル", "リンク"])

        page = 1
        total = 0
        while True:
            url = SITE_LIST_URL if page == 1 else f"{SITE_LIST_URL}?page={page}"
            self.stderr.write(f"ページ {page} 取得中: {url}")

            site_page_links = self._fetch_site_page_links(url)
            if not site_page_links:
                self.stderr.write(f"  リンクなし → 終了")
                break

            for site_page_url in site_page_links:
                result = self._fetch_site_info(site_page_url)
                if result:
                    title, link = result
                    writer.writerow([title, link])
                    total += 1
                time.sleep(0.3)

            page += 1
            time.sleep(0.5)

        self.stderr.write(f"完了: {total} 件")

    def _fetch_site_page_links(self, url: str) -> list[str]:
        """サイト一覧ページから個別サイトページへのリンク一覧を取得する"""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            self.stderr.write(f"  取得エラー: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        links: list[str] = []
        seen: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("http"):
                href = BASE_URL + href
            # /site/<slug>/ 形式のリンクを収集（一覧ページ自体や?page=は除外）
            if (
                "/site/" in href
                and href != url
                and "?page=" not in href
                and href not in seen
                and href.rstrip("/") != SITE_LIST_URL.rstrip("/")
            ):
                seen.add(href)
                links.append(href)

        return links

    def _fetch_site_info(self, site_page_url: str) -> tuple[str, str] | None:
        """個別サイトページから「〈タイトル〉のサイトへ行く」ボタンのタイトルとリンクを取得する"""
        try:
            resp = requests.get(site_page_url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            self.stderr.write(f"  取得エラー ({site_page_url}): {e}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # 「〜のサイトへ行く」テキストを含む <a> タグを探す
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if "のサイトへ行く" in text:
                link = a["href"]
                title = text.replace("のサイトへ行く", "").strip()
                return title, link

        return None
