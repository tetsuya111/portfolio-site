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
_MAX_RANK = 100_000
_JS_ESCAPE_RE = re.compile(r"\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)", re.DOTALL)
_JS_SIMPLE_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "0": "\0", "b": "\b", "f": "\f", "v": "\v"
}


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
    """JavaScript の文字列リテラルの中身（引用符を除く）のエスケープを戻す。

    \uD83C\uDFB5 のようなサロゲートペアは1文字に結合し、対のないサロゲートは
    置換文字（U+FFFD）にする（そのままだと DB 保存時に UnicodeEncodeError になるため）。
    """
    text = _JS_ESCAPE_RE.sub(_replace_js_escape, body)
    return text.encode("utf-16", "surrogatepass").decode("utf-16", "replace")


def extract_data_table_html(html: str) -> str | None:
    """<script> 内の $('#data-table').append(…) に渡されたHTML断片を出現順に連結して返す。

    呼び出しが1つもなければ None（詳細表示形式のページではない）。スクリプトは実行しない。
    """
    if "#data-table" not in html:  # 表形式のページで余計な全体解析をしない
        return None
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


def _is_number(tag: Tag) -> bool:
    return _has_class(tag, "div", "number")


def _is_title(tag: Tag) -> bool:
    return _has_class(tag, "span", "title")


def _is_artist(tag: Tag) -> bool:
    return _has_class(tag, "span", "artistLink")


def _row_parts(number: Tag) -> tuple[Tag | None, Tag | None]:
    """div.number に対応する曲名・アーティストの要素を返す。

    div.number から親をたどり、div.number をこの1つだけ含む最も外側の要素を「行」とみなして、
    その中の最初の span.title・span.artistLink を使う（実ページは 曲名 → div.number →
    アーティスト の順で同じ行に並ぶ）。行の中に曲名が無ければ None のまま返し、他の行の曲名は
    借りない。複数行が同じ親に平たく並ぶ場合は、次の div.number までに現れたものを使う。
    """
    row: Tag | None = None
    container = number.parent
    while container is not None and len(container.find_all(_is_number, limit=2)) == 1:
        row = container
        container = container.parent
    if row is not None:
        return row.find(_is_title), row.find(_is_artist)
    title = artist = None
    for tag in number.find_all_next(True):
        if _is_number(tag):
            break
        if title is None and _is_title(tag):
            title = tag
        elif artist is None and _is_artist(tag):
            artist = tag
    return title, artist


def _parse_detail_fragment(fragment: str) -> list[ChartEntry]:
    soup = BeautifulSoup(fragment, "html.parser")
    rows: list[tuple[int, str, str]] = []
    for number in soup.find_all(_is_number):
        rank_text = _clean(number.get_text())
        # 半角数字だけを順位とみなす（「+3」「１」「1_0」なども int() は受け付けてしまうため）
        if not (rank_text.isascii() and rank_text.isdigit()):
            continue
        rank = int(rank_text)
        if not 1 <= rank <= _MAX_RANK:  # DB の INTEGER を超える値や 0 以下は順位として扱わない
            continue
        title_tag, artist_tag = _row_parts(number)
        title = _clean(title_tag.get_text()) if title_tag is not None else ""
        if not title:
            continue
        artist = _clean(artist_tag.get_text()) if artist_tag is not None else ""
        rows.append((rank, title, artist))
    if not rows:
        raise ParseError("詳細表示ページから曲を取り出せませんでした")
    # 順位で安定ソートし、同順位（タイ）は直前の順位+1 に繰り下げる（DB の主キー重複を避ける）
    entries: list[ChartEntry] = []
    for rank, title, artist in sorted(rows, key=lambda row: row[0]):
        if entries and rank <= entries[-1].rank:
            rank = entries[-1].rank + 1
        entries.append(ChartEntry(rank=rank, title=title, artist=artist))
    return entries


def parse_detail_page(html: str) -> list[ChartEntry]:
    """詳細表示ページの埋め込みHTMLから順位・曲名・アーティストを取り出す。

    div.number ごとに1行を組む（1曲だけ欠けても他の行はずれない）。順位の昇順に並べ、
    同順位は捨てずに直前の順位+1 に繰り下げる（例: 1, 2, 2, 4 → 1, 2, 3, 4）。
    """
    return _parse_detail_fragment(extract_data_table_html(html) or "")


def parse_chart_page(html: str) -> list[ChartEntry]:
    """ページの中身で形式を判定し、詳細表示形式なら詳細の解析、それ以外は parse_hot100。

    詳細表示形式に見えても曲が取れなければ表の解析も試し、両方だめなら詳細表示の理由で失敗する。
    """
    fragment = extract_data_table_html(html)
    if fragment is None:
        return parse_hot100(html)
    try:
        return _parse_detail_fragment(fragment)
    except ParseError as detail_error:
        try:
            return parse_hot100(html)
        except ParseError as table_error:
            # 「この日付のデータが無い」は表の解析のほうが具体的な理由なので、そちらを優先する
            if _MISSING_CHART_TEXT in html:
                raise table_error from None
            raise detail_error from None


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
