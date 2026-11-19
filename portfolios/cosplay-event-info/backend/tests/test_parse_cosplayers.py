from pathlib import Path

from catalog.collector.parsers.cosplayers import (
    WIKIPEDIA_CATEGORY_URL,
    parse_category_page,
    parse_person_page,
)

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://ja.wikipedia.org/wiki/Category:%E3%82%B3"


def read(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_category_url_is_target_site():
    assert WIKIPEDIA_CATEGORY_URL.startswith("https://ja.wikipedia.org/wiki/Category:")


def test_category_page_lists_people_and_next_page():
    urls, next_url = parse_category_page(read("wiki_category.html"), BASE)

    assert urls == [
        "https://ja.wikipedia.org/wiki/%E3%81%82%E3%81%84",
        "https://ja.wikipedia.org/wiki/%E3%81%86%E3%81%88_(%E3%82%B3%E3%82%B9)",
    ]
    assert next_url == (
        "https://ja.wikipedia.org/w/index.php?title=Category:%E3%82%B3&pagefrom=%E3%82%8F"
    )


def test_category_page_without_next_page():
    html = '<div id="mw-pages"><ul><li><a href="/wiki/A">A</a></li></ul></div>'

    urls, next_url = parse_category_page(html, BASE)

    assert urls == ["https://ja.wikipedia.org/wiki/A"]
    assert next_url is None


def test_person_page_is_parsed():
    item = parse_person_page(read("wiki_person.html"), "https://ja.wikipedia.org/wiki/ue")

    assert item.name == "うえ"
    assert item.description == "うえは、日本のコスプレイヤー。東京都出身。"
    assert item.career == "2015年からコスプレを始める。\n2020年以降\n写真集を発売。"
    assert item.sns_links == ["https://x.com/ue_cos", "https://www.instagram.com/ue_cos/"]


def test_person_page_without_sections():
    html = '<h1 id="firstHeading">えお</h1><div class="mw-parser-output"><p>説明。</p></div>'

    item = parse_person_page(html, "https://ja.wikipedia.org/wiki/eo")

    assert item.name == "えお"
    assert item.description == "説明。"
    assert item.career == ""
    assert item.sns_links == []


def test_old_style_heading_is_supported():
    html = (
        '<h1 id="firstHeading">か</h1><div class="mw-parser-output"><p>説明。</p>'
        '<h2><span class="mw-headline" id="来歴">来歴</span></h2><p>経歴本文。</p>'
        "<h2>脚注</h2><p>脚注本文</p></div>"
    )

    item = parse_person_page(html, "https://ja.wikipedia.org/wiki/ka")

    assert item.career == "経歴本文。"


LIVE_LIKE_PERSON = """
<div id="siteNotice"><div class="mw-parser-output"><p>募金のお願い</p></div></div>
<h1 id="firstHeading">さしす</h1>
<div id="mw-content-text"><div class="mw-parser-output">
  <table class="infobox"><tr><td><a class="external" href="https://x.com/sashisu">X</a></td></tr></table>
  <p>さしすは、コスプレイヤー<sup class="reference"><a href="#c1">[1]</a></sup>。
  <a class="external" href="https://twitter.com/other_person">別の人</a>と共演。</p>
  <div class="mw-heading mw-heading2"><h2>経歴</h2><span class="mw-editsection">[<a>編集</a>]</span></div>
  <div class="mw-heading mw-heading3"><h3>2020年以降</h3><span class="mw-editsection">[<a>編集</a>]</span></div>
  <p>写真集を発売。</p>
  <div class="mw-heading mw-heading2"><h2>脚注</h2></div>
  <ol class="references"><li><a class="external" href="https://twitter.com/news_site/status/1">記事</a></li></ol>
  <div class="mw-heading mw-heading2"><h2>外部リンク</h2></div>
  <ul><li><a class="external" href="https://www.youtube.com/@sashisu">YouTube</a></li></ul>
</div></div>
"""


def test_sns_only_from_infobox_and_external_links_section():
    item = parse_person_page(LIVE_LIKE_PERSON, "https://ja.wikipedia.org/wiki/s")

    assert item.sns_links == ["https://x.com/sashisu", "https://www.youtube.com/@sashisu"]


def test_edit_section_links_and_site_notice_are_ignored():
    item = parse_person_page(LIVE_LIKE_PERSON, "https://ja.wikipedia.org/wiki/s")

    assert item.career == "2020年以降\n写真集を発売。"
    assert item.description.startswith("さしすは、コスプレイヤー。")
