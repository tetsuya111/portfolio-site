from pathlib import Path

import pytest

from app.batch.parser import (
    ChartEntry,
    ParseError,
    _unescape_js_string,
    extract_data_table_html,
    find_latest_hot100_url,
    parse_chart_page,
    parse_detail_page,
    parse_hot100,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_hot100_rows():
    entries = parse_hot100(_read("hot100.html"))
    assert entries[0] == ChartEntry(rank=1, title="The Fate Of Ophelia", artist="Taylor Swift")
    assert [e.rank for e in entries] == [1, 2, 99]
    assert entries[1].artist == "HUNTR/X: EJAE, Audrey Nuna & REI AMI"


def test_parse_mixed_artist_markup():
    entries = parse_hot100(_read("hot100.html"))
    assert entries[2] == ChartEntry(rank=99, title="3am", artist="Loe Shimmy & Don Toliver")


def test_parse_empty_raises():
    with pytest.raises(ParseError):
        parse_hot100("<html><body><table><tbody></tbody></table></body></html>")


def test_parse_skips_malformed_rows():
    html = (
        "<table><tbody>"
        "<tr><td>x</td></tr>"
        "<tr><td><b>1</b></td><td></td><td><b>Song</b><br>Artist</td></tr>"
        "</tbody></table>"
    )
    assert parse_hot100(html) == [ChartEntry(1, "Song", "Artist")]


def test_find_latest_hot100_url():
    assert (
        find_latest_hot100_url(_read("top.html"))
        == "https://billboard.mryogaku.com/php/dispHot100.php?date=2026-11-14"
    )


def test_find_latest_hot100_url_relative():
    html = '<a href="./php/dispHot100.php?date=2026-01-03">x</a>'
    assert (
        find_latest_hot100_url(html)
        == "https://billboard.mryogaku.com/php/dispHot100.php?date=2026-01-03"
    )


def test_find_latest_ignores_foreign_links():
    html = (
        '<a href="https://evil.example/php/dispHot100.php?date=2026-01-03">x</a>'
        '<a href="/php/dispHot100.php?date=2026-01-10">y</a>'
    )
    assert find_latest_hot100_url(html).endswith("date=2026-01-10")


def test_find_latest_missing_raises():
    with pytest.raises(ParseError):
        find_latest_hot100_url("<html><a href='/php/chart.php?date=2026-01-03'>x</a></html>")


def test_parse_missing_chart_file_message():
    html = (
        "<body><div>Billboard Hot 100 : 2001-11-17</div>"
        "<p>チャートファイルが見つかりません: 2001-11-17</p></body>"
    )
    with pytest.raises(ParseError, match="この日付のチャートデータがありません"):
        parse_hot100(html)


def test_unescape_js_string():
    assert _unescape_js_string(r"a\"b\'c\\d\/e’f\x41\n") == "a\"b'c\\d/e’fA\n"


def test_extract_data_table_html_joins_calls_in_order():
    fragment = extract_data_table_html(_read("detail.html"))
    assert fragment is not None
    assert fragment.index(">2</div>") < fragment.index(">1</div>") < fragment.index(">3</div>")
    assert "Choosin’ Texas" in fragment
    assert "</span>" in fragment and "\\" not in fragment


def test_extract_ignores_other_targets():
    assert "Decoy" not in extract_data_table_html(_read("detail.html"))


def test_extract_returns_none_without_append():
    assert extract_data_table_html(_read("hot100.html")) is None


def test_parse_detail_page_rows():
    assert parse_detail_page(_read("detail.html")) == [
        ChartEntry(1, "A Bar Song (Tipsy)", "Shaboozey"),
        ChartEntry(2, "Choosin’ Texas", "Ella Langley"),
        ChartEntry(3, "Rock & Roll", "Simon & Garfunkel"),
    ]


def _detail(*rows: str) -> str:
    calls = "".join(f'$("#data-table").append("{r}");' for r in rows)
    return f"<script>{calls}</script>"


def test_parse_detail_missing_artist_does_not_shift():
    html = _detail(
        "<div class='number'>1</div><span class='title'>A</span>",
        "<div class='number'>2</div><span class='title'>B</span><span class='artistLink'>X</span>",
    )
    assert parse_detail_page(html) == [ChartEntry(1, "A", ""), ChartEntry(2, "B", "X")]


def test_parse_detail_duplicate_rank_moves_down():
    # 同順位（タイ）は捨てずに、それまでの最大順位+1 に繰り下げて主キーの重複を避ける
    html = _detail(
        "<div class='number'>1</div><span class='title'>First</span>",
        "<div class='number'>1</div><span class='title'>Second</span>",
        "<div class='number'>3</div><span class='title'>Third</span>",
    )
    assert parse_detail_page(html) == [
        ChartEntry(1, "First", ""),
        ChartEntry(2, "Second", ""),
        ChartEntry(3, "Third", ""),
    ]


def test_parse_detail_real_layout_title_before_number():
    # 実ページ（2026-11-14 確認）は同じセル内で 曲名 → div.number → アーティスト の順
    assert parse_detail_page(_read("detail_real.html")) == [
        ChartEntry(1, "A Bar Song (Tipsy)", "Shaboozey"),
        ChartEntry(2, "Ordinary", "Alex Warren"),
        ChartEntry(3, "Choosin’ Texas", "Ella Langley"),
        ChartEntry(4, "Blinding Lights", "The Weeknd"),
    ]


def test_parse_detail_skips_bad_rank_and_empty_title():
    html = _detail(
        "<div class='number'>x</div><span class='title'>Bad</span>",
        "<div class='number'>2</div><span class='title'> </span>",
        "<div class='number'>3</div><span class='title'>Ok</span>",
    )
    assert parse_detail_page(html) == [ChartEntry(3, "Ok", "")]


def test_parse_detail_empty_raises():
    with pytest.raises(ParseError, match="詳細表示ページから曲を取り出せませんでした"):
        parse_detail_page(_detail("<p>no rows</p>"))


def test_parse_chart_page_dispatches():
    assert parse_chart_page(_read("detail.html"))[0].title == "A Bar Song (Tipsy)"
    assert parse_chart_page(_read("hot100.html")) == parse_hot100(_read("hot100.html"))
