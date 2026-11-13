"""ビルボード・データベースのHTML解析。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.batch.urls import TOP_URL, InvalidChartUrl, resolve_chart_url

_WS_RE = re.compile(r"\s+")
# 指定日付のデータがないとき dispHot100.php が表示する文言
_MISSING_CHART_TEXT = "チャートファイルが見つかりません"


@dataclass(frozen=True)
class ChartEntry:
    rank: int
    title: str
    artist: str


class ParseError(ValueError):
    """ページから期待したデータを取り出せない。"""


def _clean(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _parse_row(row: Tag) -> ChartEntry | None:
    cells = row.find_all("td", recursive=False)
    if len(cells) < 3:
        return None
    rank_tag = cells[0].find("b")
    title_tag = cells[2].find("b")
    if rank_tag is None or title_tag is None:
        return None
    try:
        rank = int(_clean(rank_tag.get_text()))
    except ValueError:
        return None
    title = _clean(title_tag.get_text())
    # アーティスト名は曲名の <b> の後ろにあるテキスト（<a> 有無が混在する）
    artist = _clean(
        "".join(
            sib.get_text() if isinstance(sib, Tag) else str(sib)
            for sib in title_tag.next_siblings
        )
    )
    if not title:
        return None
    return ChartEntry(rank=rank, title=title, artist=artist)


def parse_hot100(html: str) -> list[ChartEntry]:
    """dispHot100.php の表から順位・曲名・アーティストを取り出す。"""
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    for row in soup.select("table tbody tr"):
        entry = _parse_row(row)
        if entry is not None:
            entries.append(entry)
    if not entries:
        if _MISSING_CHART_TEXT in soup.get_text():
            raise ParseError(
                "この日付のチャートデータがありません（別の週のURLを指定してください）"
            )
        raise ParseError("チャートの曲が見つかりませんでした")
    return entries


def find_latest_hot100_url(html: str) -> str:
    """トップページから最新週の Hot 100 全順位ページのURLを探す。"""
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select('a[href*="dispHot100.php"]'):
        href = urljoin(TOP_URL, str(link.get("href", "")))
        try:
            target = resolve_chart_url(href)
        except InvalidChartUrl:
            continue
        if target.kind == "hot100":
            return target.url
    raise ParseError("最新の Hot 100 ページへのリンクが見つかりませんでした")
