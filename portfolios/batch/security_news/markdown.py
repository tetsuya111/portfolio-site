"""セキュリティ記事を、静的サイトにそのまま置ける Markdown にする（無害化は it_news.markdown と同じ）。"""

from __future__ import annotations

from it_news.markdown import (
    _one_line,
    ai_notice,
    check_title_and_date,
    frontmatter_lines,
    glossary_lines,
    reference_lines,
    sanitize_markdown,
    valid_glossary,
    valid_references,
)

GLOSSARY = "glossary"
NOTES = "notes"
EMPTY_NOTES = "特記事項はありません。"

# (見出し, 記事のキー)。この順で h2 を並べ、最後に「参考リンク」を付ける
SECTIONS = (
    ("概要", "overview"),
    ("脆弱性の詳細", "details"),
    ("具体的な対応方法", "mitigation"),
    ("IT業界における経緯", "history"),
    ("関連技術", "relatedTech"),
    ("IT用語の解説", GLOSSARY),
    ("備考", NOTES),
)


def build_security_markdown(
    *,
    article: dict,
    references: list[dict],
    date: str,
    source_url: str,
    generator: str,
    tags: list[str],
) -> str:
    """frontmatter つきのセキュリティ記事の Markdown を返す。

    タイトル・日付が不正、備考以外の節が空、用語解説が 0 件、http(s) の参考リンクが 0 件なら ValueError。
    節の中の見出しは h3 以下に下げ、構成の見出し（h2）と並ばないようにする。
    """
    title = _one_line(article.get("title", ""))
    check_title_and_date(title, date)
    refs = valid_references(references)
    if not refs:
        raise ValueError("参考リンク（http/https）がありません")
    glossary = valid_glossary(article.get(GLOSSARY, []))
    if not glossary:
        raise ValueError("用語解説がありません")

    lines = frontmatter_lines(
        title=title, date=date, tags=tags, generated_tags=article.get("tags", []),
        description=article.get("description", ""), source_url=source_url, generator=generator,
    )
    lines += ["", ai_notice(generator, date), ""]
    for heading, key in SECTIONS:
        if key == GLOSSARY:
            body = glossary_lines(glossary)
        else:
            text = str(article.get(key, "")).strip()
            if not text and key == NOTES:
                text = EMPTY_NOTES
            if not text:
                raise ValueError(f"{heading}がありません")
            # 節ごとに無害化する（閉じていないコードブロックも節の中で閉じ、次の見出しを飲み込ませない）
            body = [sanitize_markdown(text, min_heading=3)]
        lines += [f"## {heading}", "", *body, ""]
    lines += ["## 参考リンク", "", *reference_lines(refs)]
    return "\n".join(lines) + "\n"
