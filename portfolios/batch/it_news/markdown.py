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
# - コードの中は Markdown がエスケープするのでそのまま残す。コードの判定は CommonMark の規則に合わせ、
#   判定がずれうる書き方はコードとして扱わない（安全側）:
#   - インラインコードは1行の中で閉じるものだけ。閉じていない ` はエスケープし、次の行に続くコードを作らせない
#   - コードブロックは行頭（字下げなし）の ``` / ~~~ で始まるものだけ（リストの中などは容器の終わりで閉じるため）
# - 画像（![…](…)）は残さない（外部のサーバーへ閲覧者のブラウザから接続させないため）
_SAFE_LINK = re.compile(r"(?<!!)\[([^\[\]\n`\\<]+)\]\((https?://[^\s()<>\\]+|#[A-Za-z0-9_-]+)\)")
# インラインコード: 同じ長さのバッククォートの並びで囲む（前後にバッククォートが続かない。\` は開始にならない）
_CODE_SPAN = re.compile(r"(?<![`\\])(`+)(?!`)(.+?)(?<!`)\1(?!`)")
# コードブロックの開始: 行頭の 3 つ以上の ` か ~（` の場合、情報文字列に ` を含むものはコードブロックにならない）
_FENCE_OPEN = re.compile(r"^(`{3,}|~{3,})(.*)$")
# 見出しの h1: ATX（# 見出し。引用 > の中を含む）と setext（次の行が ===）
_ATX_H1 = re.compile(r"^((?: {0,3}>[ ]?)*)( {0,3})#(?=\s|$)")
# ATX 見出し（引用 > の中を含む）。min_heading より浅い見出しを下げるのに使う
_ATX = re.compile(r"^((?: {0,3}>[ ]?)*)( {0,3})(#{1,6})(?=\s|$)")
_SETEXT_H1 = re.compile(r"^( {0,3})(=+)([ \t]*)$")
_REFERENCE_URL = re.compile(r"^https?://[^\s<>\"\\\x00-\x1f\x7f]+$")
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
    text = (
        text.replace("\\", "\\\\")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("`", "\\`")  # 1行の中で閉じていない `（コードを次の行へ続かせない）
        .replace("<", "&lt;")
    )
    for i, link in enumerate(links):
        text = text.replace(_PLACEHOLDER.format(i), link)
    return text


def _sanitize_text(text: str) -> str:
    """1行の中の文字列を無害化する。1行の中で閉じるインラインコードだけをそのまま残す。"""
    out, pos = [], 0
    for m in _CODE_SPAN.finditer(text):
        out.append(_escape_text(text[pos : m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_escape_text(text[pos:]))
    return "".join(out)


def _sanitize_line(line: str, min_heading: int = 2) -> str:
    """コードブロックの外の1行。ページの h1 と重ならないよう、本文の h1 は h2 にする。

    min_heading が 3 以上なら、それより浅い ATX 見出し（# / ## …）もその深さまで下げる（記事の節の見出しと並ばないようにする）。
    """
    setext = _SETEXT_H1.match(line)
    if setext:
        return setext.group(1) + "-" * len(setext.group(2)) + setext.group(3)
    if min_heading <= 2:
        line = _ATX_H1.sub(r"\1\2##", line, count=1)
    else:
        line = _ATX.sub(lambda m: m.group(1) + m.group(2) + "#" * max(len(m.group(3)), min_heading), line, count=1)
    return _sanitize_text(line)


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


def sanitize_markdown(md: str, min_heading: int = 2) -> str:
    """生の HTML と、http(s)・# 以外へのリンクを無効にし、h1 を h2（min_heading を指定したらその深さ）に下げる。

    コードブロックの中は変えない。
    """
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
        result.append(_sanitize_line(line, min_heading))
    if fence is not None:
        # 閉じていないコードブロックを閉じる。閉じないと、後ろにつなげる別の節（参考情報など）のコードの開始が
        # 閉じとして扱われ、無害化していない行（コードのつもりの行）が HTML として出てしまう
        result.append(fence[0] * fence[1])
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


def valid_references(references: list[dict]) -> list[dict]:
    """参考リンクに使える（http(s) で、空白・改行・制御文字・<>"\\ を含まない）ものだけを返す。

    それ以外の URL は、リンクの行を壊して HTML を差し込めるため使わない。
    """
    return [r for r in references if _REFERENCE_URL.match(str(r.get("url", "")))]


def valid_glossary(glossary: list[dict]) -> list[dict]:
    return [g for g in glossary if _one_line(g.get("term", "")) and _one_line(g.get("description", ""))]


def frontmatter_lines(*, title: str, date: str, tags: list[str], generated_tags: list[str], description: str,
                      source_url: str, generator: str) -> list[str]:
    """frontmatter（区切りの --- を含む）の行。値は JSON で書く（JSON の文字列・配列は YAML としても正しく、エスケープが確実なため）。"""
    fm: dict[str, object] = {"title": title, "date": date, "tags": _tags(tags, list(generated_tags))}
    description = _one_line(description)
    if description:
        fm["description"] = description
    fm["sourceUrl"] = source_url
    fm["generator"] = generator
    return ["---", *(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items()), "---"]


def ai_notice(generator: str, date: str) -> str:
    return (
        f"> この記事は AI（{_sanitize_text(generator)}）が {date} に自動で作成しました。"
        "内容の正確性は参考リンクの出典で確認してください。"
    )


def glossary_lines(glossary: list[dict]) -> list[str]:
    return [
        f"- **{_sanitize_text(_one_line(g['term']))}**: {_sanitize_text(_one_line(g['description']))}" for g in glossary
    ]


def reference_lines(refs: list[dict]) -> list[str]:
    lines = []
    for i, r in enumerate(refs, 1):
        # 角かっこは無害化の前に全角にする（後にすると、エスケープの \ が画面に残る）
        label = _sanitize_text(_one_line(r.get("title") or r["url"]).replace("[", "［").replace("]", "］"))
        url = str(r["url"]).replace("(", "%28").replace(")", "%29")
        lines.append(f"{i}. [{label}]({url})")
    return lines


def check_title_and_date(title: str, date: str) -> None:
    if not title:
        raise ValueError("タイトルが空です")
    if not _valid_date(date):
        raise ValueError(f"日付が不正です: {date}")


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

    条件（タイトル・日付・参考情報・用語解説 1 件以上・http(s) の参考リンク 1 件以上）を満たさなければ ValueError。
    """
    title = _one_line(article.get("title", ""))
    check_title_and_date(title, date)
    refs = valid_references(references)
    if not refs:
        raise ValueError("参考リンク（http/https）がありません")
    glossary = valid_glossary(article.get("glossary", []))
    if not glossary:
        raise ValueError("用語解説がありません")
    background = str(article.get("background", "")).strip()
    if not background:
        raise ValueError("参考情報がありません")

    lines = frontmatter_lines(
        title=title, date=date, tags=tags, generated_tags=article.get("tags", []),
        description=article.get("description", ""), source_url=source_url, generator=generator,
    )
    lines += ["", ai_notice(generator, date)]
    lines += ["", sanitize_markdown(str(article.get("body", "")).strip()), ""]
    lines += ["## 参考情報", "", sanitize_markdown(background), ""]
    lines += ["## 用語解説", "", *glossary_lines(glossary)]
    lines += ["", "## 参考リンク", "", *reference_lines(refs)]
    return "\n".join(lines) + "\n"
