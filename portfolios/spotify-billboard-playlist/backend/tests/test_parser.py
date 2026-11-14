from pathlib import Path

import pytest

from app.batch.parser import (
    ChartEntry,
    ParseError,
    _unescape_js_string,
    extract_data_table_html,
    find_latest_hot100_url,
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
