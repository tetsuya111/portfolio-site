"""Wikipedia（MediaWiki）のページからコスプレイヤーの情報を抽出する（CP-1）。"""

import re
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urlsplit

from bs4 import BeautifulSoup, Tag

from catalog.collector.parsers import absolute_http_url

WIKIPEDIA_CATEGORY_URL = "https://ja.wikipedia.org/wiki/Category:%E3%82%B3%E3%82%B9%E3%83%97%E3%83%AC%E3%82%A4%E3%83%A4%E3%83%BC"

CAREER_KEYWORDS = ("経歴", "来歴", "略歴", "人物")
SNS_HOSTS = (
    "x.com",
    "twitter.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "facebook.com",
    "threads.net",
    "threads.com",
)
MAX_TEXT_LENGTH = 3000

_FOOTNOTE = re.compile(r"\[(?:注\s*)?\d+\]")
_DISAMBIGUATION = re.compile(r"\s*[（(][^）)]*[）)]\s*$")


@dataclass(frozen=True)
class CosplayerItem:
    name: str
    sns_links: list[str] = field(default_factory=list)
    career: str = ""
    description: str = ""
    notes: str = ""


def parse_category_page(html: str, base_url: str) -> tuple[list[str], str | None]:
    """カテゴリーページから人物ページの URL と「次のページ」の URL を返す。"""
    soup = BeautifulSoup(html, "html.parser")
    pages = soup.select_one("#mw-pages")
    if pages is None:
        return [], None

    urls: list[str] = []
    for a in pages.select("li a[href]"):
        url = absolute_http_url(str(a["href"]), base_url)
        if url and "/wiki/" in url and "Category:" not in url and url not in urls:
            urls.append(url)

    next_url = None
    for a in pages.find_all("a", href=True):
        if a.get_text(strip=True) == "次のページ":
            next_url = urldefrag(absolute_http_url(str(a["href"]), base_url)).url or None
            break
    return urls, next_url


def _clean_text(node: Tag) -> str:
    for sup in node.select("sup.reference"):
        sup.decompose()
    text = _FOOTNOTE.sub("", node.get_text(""))
    return " ".join(text.split())


def _heading_level(el: Tag) -> int | None:
    """見出しなら 2〜4 の階層を返す（新形式 div.mw-heading と旧形式 h2 の両方）。"""
    if el.name in ("h2", "h3", "h4"):
        return int(el.name[1])
    if el.name == "div":
        for cls in el.get("class") or []:
            if cls in ("mw-heading2", "mw-heading3", "mw-heading4"):
                return int(cls[-1])
    return None


def _career(body: Tag) -> str:
    lines: list[str] = []
    in_section = False
    for el in body.find_all(recursive=False):
        level = _heading_level(el)
        if level == 2:
            in_section = any(k in el.get_text() for k in CAREER_KEYWORDS)
            continue
        if not in_section:
            continue
        if level is not None or el.name == "p":
            text = _clean_text(el)
            if text:
                lines.append(text)
        elif el.name in ("ul", "ol"):
            lines.extend(t for li in el.find_all("li") if (t := _clean_text(li)))
    return "\n".join(lines)[:MAX_TEXT_LENGTH]


def _description(body: Tag) -> str:
    for p in body.find_all("p", recursive=False):
        text = _clean_text(p)
        if text:
            return text[:MAX_TEXT_LENGTH]
    return ""


def _is_sns(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in SNS_HOSTS)


def _sns_links(body: Tag, base_url: str) -> list[str]:
    links: list[str] = []
    for a in body.find_all("a", href=True):
        url = absolute_http_url(str(a["href"]), base_url)
        if url and _is_sns(url) and url not in links:
            links.append(url)
    return links


def parse_person_page(html: str, url: str) -> CosplayerItem:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.select_one("#firstHeading")
    name = _DISAMBIGUATION.sub("", heading.get_text(strip=True)) if heading else ""
    body = soup.select_one(".mw-parser-output")
    if body is None:
        return CosplayerItem(name=name)
    # 本文の抽出で脚注を消すため、SNS は先に集める
    sns = _sns_links(body, url)
    return CosplayerItem(
        name=name,
        sns_links=sns,
        career=_career(body),
        description=_description(body),
    )
