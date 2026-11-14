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

# 詳細表示ページ（alltime.php 等）が <script> で $('#data-table').append(…) に渡す文字列。
# 入れ子の量指定を持たない形にして、入力長に対して線形に動くようにしている。
_JS_STRING = r"\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'"
_JS_STRING_RE = re.compile(_JS_STRING)
_DATA_TABLE_APPEND_RE = re.compile(
    r"\$\(\s*(['\"])#data-table\1\s*\)\s*\.append\(\s*"
    rf"((?:{_JS_STRING})(?:\s*\+\s*(?:{_JS_STRING}))*)"
    r"\s*\)"
)
_JS_ESCAPE_RE = re.compile(r"\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)", re.DOTALL)
_JS_SIMPLE_ESCAPES = {"n": "\n", "t": "\t", "r": "\r"}


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


def _replace_js_escape(match: re.Match[str]) -> str:
    code = match.group(1)
    if len(code) > 1:  # uXXXX / xXX
        return chr(int(code[1:], 16))
    return _JS_SIMPLE_ESCAPES.get(code, code)


def _unescape_js_string(body: str) -> str:
    """JavaScript の文字列リテラルの中身（引用符を除く）のエスケープを戻す。"""
    return _JS_ESCAPE_RE.sub(_replace_js_escape, body)


def extract_data_table_html(html: str) -> str | None:
    """<script> 内の $('#data-table').append(…) に渡されたHTML断片を出現順に連結して返す。

    呼び出しが1つもなければ None（詳細表示形式のページではない）。スクリプトは実行しない。
    """
    soup = BeautifulSoup(html, "html.parser")
    script = "\n".join(tag.get_text() for tag in soup.find_all("script"))
    parts: list[str] = []
    found = False
    for call in _DATA_TABLE_APPEND_RE.finditer(script):
        found = True
        for literal in _JS_STRING_RE.finditer(call.group(2)):
            parts.append(_unescape_js_string(literal.group(0)[1:-1]))
    return "".join(parts) if found else None


def _has_class(tag: Tag, name: str, class_name: str) -> bool:
    return tag.name == name and class_name in (tag.get("class") or [])


def parse_detail_page(html: str) -> list[ChartEntry]:
    """詳細表示ページの埋め込みHTMLから順位・曲名・アーティストを取り出す。

    div.number を行の区切りとし、次の div.number までに現れた最初の span.title・
    span.artistLink をその行の曲名・アーティストとする（1曲だけ欠けても他の行はずれない）。
    """
    fragment = extract_data_table_html(html) or ""
    soup = BeautifulSoup(fragment, "html.parser")
    rows: list[dict[str, str | None]] = []
    for tag in soup.find_all(True):
        if _has_class(tag, "div", "number"):
            rows.append({"rank": tag.get_text(), "title": None, "artist": None})
        elif not rows:
            continue
        elif _has_class(tag, "span", "title") and rows[-1]["title"] is None:
            rows[-1]["title"] = tag.get_text()
        elif _has_class(tag, "span", "artistLink") and rows[-1]["artist"] is None:
            rows[-1]["artist"] = tag.get_text()

    by_rank: dict[int, ChartEntry] = {}
    for row in rows:
        try:
            rank = int(_clean(row["rank"] or ""))
        except ValueError:
            continue
        title = _clean(row["title"] or "")
        if not title or rank in by_rank:
            continue
        by_rank[rank] = ChartEntry(rank=rank, title=title, artist=_clean(row["artist"] or ""))
    if not by_rank:
        raise ParseError("詳細表示ページから曲を取り出せませんでした")
    return [by_rank[rank] for rank in sorted(by_rank)]


def parse_chart_page(html: str) -> list[ChartEntry]:
    """ページの中身で形式を判定し、詳細表示形式なら parse_detail_page、それ以外は parse_hot100。"""
    if extract_data_table_html(html) is not None:
        return parse_detail_page(html)
    return parse_hot100(html)


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
