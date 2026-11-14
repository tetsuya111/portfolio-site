"""LLM が書いた記事を、静的サイトにそのまま置ける Markdown にする。

Astro などの Markdown 変換は生の HTML をそのまま出力するため、LLM の出力は信用せず無害化してから使う。
"""

from __future__ import annotations

import json
import re
from datetime import datetime

# 方針: 危険な書き方を1つずつ探して消す（取りこぼしうる）のではなく、許す形だけを残して残りをすべて文字にする。
# - 許すリンクは、1行の中で完結する [文字](http(s)://… または #id) だけ。それ以外の [ ] はすべて \[ \] にエスケープするので、
#   参照形式・複数行・タイトル付き・入れ子のかっこ・文字参照（&#106;avascript:）など、どの書き方でもリンクや画像にならない。
# - コードの外の < はすべて &lt; にする（生の HTML・自動リンクにならない）。\ も \\ にして、エスケープを打ち消せないようにする。
# - コードの中は Markdown がエスケープするのでそのまま残す。コードの判定は CommonMark の規則に合わせる。
_SAFE_LINK = re.compile(r"(!?)\[([^\[\]\n`\\<]+)\]\((https?://[^\s()<>\\]+|#[A-Za-z0-9_-]+)\)")
# インラインコード: 同じ長さのバッククォートの並びで囲む（前後にバッククォートが続かない。\` は開始にならない）
_CODE_SPAN = re.compile(r"(?<![`\\])(`+)(?!`)(.+?)(?<!`)\1(?!`)")
# コードブロックの開始: 3 つ以上の ` か ~（` の場合、情報文字列に ` を含むものはコードブロックにならない）
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_PLACEHOLDER = "\x00{}\x00"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MAX_ARTICLE_TAGS = 5


def _escape_text(text: str) -> str:
    """コードの外の文字列を無害化する（許すリンクだけを残す）。"""
    text = text.replace("\x00", "")
    links: list[str] = []

    def keep(m: re.Match[str]) -> str:
        links.append(m.group(0))
        return _PLACEHOLDER.format(len(links) - 1)

    text = _SAFE_LINK.sub(keep, text)
    text = text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("<", "&lt;")
    for i, link in enumerate(links):
        text = text.replace(_PLACEHOLDER.format(i), link)
    return text


def _sanitize_line(line: str) -> str:
    """コードブロックの外の1行。"""
    if re.match(r"^ {0,3}#(\s|$)", line):
        line = "#" + line.lstrip(" ")  # ページの h1 と重ならないよう、本文の見出しは h2 以下にする
    out, pos = [], 0
    for m in _CODE_SPAN.finditer(line):
        out.append(_escape_text(line[pos : m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_escape_text(line[pos:]))
    return "".join(out)


def _sanitize_text(text: str) -> str:
    """見出し以外の1行分の短い文字列（用語解説など）。"""
    return _sanitize_line(text) if not text.lstrip(" ").startswith("#") else _escape_text(text)


def _fence_open(line: str) -> tuple[str, int] | None:
    m = _FENCE_OPEN.match(line)
    if not m:
        return None
    marker, info = m.group(1), m.group(2)
    if marker[0] == "`" and "`" in info:
        return None
    return marker[0], len(marker)


def _closes_fence(line: str, char: str, length: int) -> bool:
    return re.match(rf"^ {{0,3}}{re.escape(char)}{{{length},}}[ \t]*$", line) is not None


def sanitize_markdown(md: str) -> str:
    """生の HTML と、http(s)・# 以外へのリンクを無効にし、h1 を h2 に下げる。コードブロックの中は変えない。"""
    result: list[str] = []
    fence: tuple[str, int] | None = None
    for line in md.split("\n"):
        if fence is not None:
            result.append(line)
            if _closes_fence(line, *fence):
                fence = None
            continue
        opened = _fence_open(line)
        if opened:
            fence = opened
            result.append(line)
            continue
        result.append(_sanitize_line(line))
    return "\n".join(result)


def _one_line(text: str) -> str:
    return " ".join(str(text).split())


def _valid_date(date: str) -> bool:
    if not _DATE.match(date):
        return False
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _tags(fixed: list[str], generated: list[str]) -> list[str]:
    tags: list[str] = []
    for t in [*fixed, *generated[:_MAX_ARTICLE_TAGS]]:
        t = _one_line(t)
        if t and t not in tags:
            tags.append(t)
    return tags


def build_article_markdown(
    *,
    article: dict,
    references: list[dict],
    date: str,
    source_url: str,
    generator: str,
    tags: list[str],
) -> str:
    """frontmatter（title・date・tags・description・sourceUrl・generator）つきの Markdown を返す。

    frontmatter の値は JSON で書く（JSON の文字列・配列は YAML としても正しく、エスケープが確実なため）。
    条件（タイトル・日付・参考情報・用語解説 1 件以上・http(s) の参考リンク 1 件以上）を満たさなければ ValueError。
    """
    title = _one_line(article.get("title", ""))
    if not title:
        raise ValueError("タイトルが空です")
    if not _valid_date(date):
        raise ValueError(f"日付が不正です: {date}")
    refs = [r for r in references if str(r.get("url", "")).startswith(("https://", "http://"))]
    if not refs:
        raise ValueError("参考リンク（http/https）がありません")
    glossary = [g for g in article.get("glossary", []) if _one_line(g.get("term", "")) and _one_line(g.get("description", ""))]
    if not glossary:
        raise ValueError("用語解説がありません")
    background = str(article.get("background", "")).strip()
    if not background:
        raise ValueError("参考情報がありません")

    fm = {
        "title": title,
        "date": date,
        "tags": _tags(tags, list(article.get("tags", []))),
    }
    description = _one_line(article.get("description", ""))
    if description:
        fm["description"] = description
    fm["sourceUrl"] = source_url
    fm["generator"] = generator

    lines = ["---", *(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items()), "---", ""]
    lines.append(
        f"> この記事は AI（{_sanitize_text(generator)}）が {date} に自動で作成しました。"
        "内容の正確性は参考リンクの出典で確認してください。"
    )
    lines += ["", sanitize_markdown(str(article.get("body", "")).strip()), ""]
    lines += ["## 参考情報", "", sanitize_markdown(background), ""]
    lines += ["## 用語解説", ""]
    lines += [
        f"- **{_sanitize_text(_one_line(g['term']))}**: {_sanitize_text(_one_line(g['description']))}" for g in glossary
    ]
    lines += ["", "## 参考リンク", ""]
    for i, r in enumerate(refs, 1):
        label = _sanitize_text(_one_line(r.get("title") or r["url"])).replace("[", "［").replace("]", "］")
        url = str(r["url"]).replace(" ", "%20").replace("(", "%28").replace(")", "%29")
        lines.append(f"{i}. [{label}]({url})")
    return "\n".join(lines) + "\n"
