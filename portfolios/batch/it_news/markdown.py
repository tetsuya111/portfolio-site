"""LLM が書いた記事を、静的サイトにそのまま置ける Markdown にする。

Astro などの Markdown 変換は生の HTML をそのまま出力するため、LLM の出力は信用せず無害化してから使う。
"""

from __future__ import annotations

import json
import re
from datetime import datetime

# 本文のリンク [text](url "title")。url の中の (...) は1段だけ許す（javascript:alert(1) を1つのリンクとして扱う）
_LINK = re.compile(r'(!?)\[([^\]\n]*)\]\(\s*((?:[^()\s]|\([^()\s]*\))*)(?:\s+"[^"\n]*")?\s*\)')
_REF_DEF = re.compile(r"^\s{0,3}\[[^\]\n]+\]:\s*(\S+)")
_INLINE_CODE = re.compile(r"(`+)(.+?)\1")
_FENCE = re.compile(r"^\s{0,3}(```|~~~)")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MAX_ARTICLE_TAGS = 5


def _is_allowed_url(url: str) -> bool:
    return url.startswith(("https://", "http://", "#"))


def _sanitize_text(text: str) -> str:
    """コードの外の1行分の文字列を無害化する。"""

    def unlink(m: re.Match[str]) -> str:
        # 画像（![alt](url)）も含め、許さないリンク先は文字だけにする
        return m.group(0) if _is_allowed_url(m.group(3)) else m.group(2)

    text = _LINK.sub(unlink, text)
    return text.replace("<", "&lt;")


def _sanitize_line(line: str) -> str | None:
    """コードブロックの外の1行。None ならその行を消す。"""
    ref = _REF_DEF.match(line)
    if ref:
        return line if _is_allowed_url(ref.group(1)) else None
    if re.match(r"^#(\s|$)", line):
        line = "#" + line  # ページの h1 と重ならないよう、本文の見出しは h2 以下にする
    # インラインコードの中は Markdown がエスケープするので、そのまま残す
    out, pos = [], 0
    for m in _INLINE_CODE.finditer(line):
        out.append(_sanitize_text(line[pos : m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_sanitize_text(line[pos:]))
    return "".join(out)


def sanitize_markdown(md: str) -> str:
    """生の HTML・http(s) と # 以外のリンクを無効にし、h1 を h2 に下げる。コードブロックの中は変えない。"""
    result: list[str] = []
    fence: str | None = None
    for line in md.split("\n"):
        m = _FENCE.match(line)
        if fence is not None:
            result.append(line)
            if m and m.group(1) == fence:
                fence = None
            continue
        if m:
            fence = m.group(1)
            result.append(line)
            continue
        cleaned = _sanitize_line(line)
        if cleaned is not None:
            result.append(cleaned)
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
