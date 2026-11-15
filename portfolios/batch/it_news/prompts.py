"""題材選定と記事執筆のプロンプト・JSON スキーマ・応答の検証。"""

from __future__ import annotations

from typing import Callable

MAX_TOPICS = 15

# プロンプトは英語にする（検索クエリが英語になり、英語の一次情報に当たりやすくなる）。出力は日本語に指定する
SYSTEM = (
    "You are a technology journalist covering the IT industry. Base every fact on the search results, "
    "and never present speculation or unverified information as fact. "
    "Write all output text in Japanese."
)

TOPICS_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "sourceUrl": {"type": "string"},
                    "importance": {"type": "integer"},
                    "reason": {"type": "string"},
                },
                "required": ["title", "summary", "sourceUrl", "importance", "reason"],
            },
        }
    },
    "required": ["topics"],
}

ARTICLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "slug": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "body": {"type": "string"},
        "background": {"type": "string"},
        "glossary": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"term": {"type": "string"}, "description": {"type": "string"}},
                "required": ["term", "description"],
            },
        },
    },
    "required": ["title", "slug", "description", "tags", "body", "background", "glossary"],
}


def topics_request(recent_titles: list[str]) -> tuple[list[dict], dict]:
    covered = "\n".join(f"- {t}" for t in recent_titles) or "(none)"
    user = (
        f"List up to {MAX_TOPICS} important news items in IT and software development published in the last 24-48 hours.\n"
        "- importance: an integer from 1 to 10, ranked by impact on developers and the IT industry "
        "(number of affected users, security severity, changes to standards or major products).\n"
        "- sourceUrl: the URL of the primary source for the news "
        "(official announcement, official blog, or reputable news outlet).\n"
        "- title, summary, reason: write these in Japanese.\n"
        "Exclude topics already covered by the following articles (titles are in Japanese).\n"
        f"{covered}"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], TOPICS_SCHEMA


def article_request(topic: dict) -> tuple[list[dict], dict]:
    user = (
        "Write a technical article about the following IT news. "
        "Write every field in Japanese, except slug and the names of technologies and products.\n"
        f"Topic: {topic['title']}\nSummary: {topic['summary']}\nSource: {topic['sourceUrl']}\n\n"
        "- title: the article title (at most 60 Japanese characters)\n"
        "- slug: a short string of lowercase English letters, digits and hyphens describing the content (e.g. astro-7-release)\n"
        "- description: a summary in one or two sentences\n"
        "- tags: 1 to 5 related technology or product names\n"
        "- body: the article body in Markdown (800-1,500 Japanese characters; headings start at ##; "
        "cover what happened, the key technical points and the impact on developers; "
        "add a citation number such as [1] to each sentence based on the search results; do not use HTML tags)\n"
        "- background: reference information in Markdown (background, history, related technologies and trends)\n"
        "- glossary: 2 to 6 technical terms used in the body, each with a short explanation for beginners\n"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], ARTICLE_SCHEMA


def _str(v: object) -> str:
    return v.strip() if isinstance(v, str) else ""


def _short(v: object, limit: int = 80) -> str:
    """ログ用に値を短く表す（長い応答でログが埋まらないようにする）。"""
    s = repr(v)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def validate_topics(data: object, log: Callable[[str], None] = lambda _: None) -> list[dict]:
    """形が正しい題材だけを返す（http(s) の出典・空でないタイトル。importance は 1〜10 に丸める）。

    受け取った件数と、除いた題材ごとの理由を log に出す（題材が 0 件になったときの原因を追えるようにする）。
    """
    if not isinstance(data, dict) or not isinstance(data.get("topics"), list):
        raise ValueError("題材の応答の形が不正です（topics の配列がありません）")
    log(f"Perplexity から受け取った題材: {len(data['topics'])} 件")
    topics = []
    for i, t in enumerate(data["topics"], 1):
        if not isinstance(t, dict):
            log(f"  除外 {i}: 題材がオブジェクトではない（{_short(t)}）")
            continue
        title, url = _str(t.get("title")), _str(t.get("sourceUrl"))
        if not title:
            log(f"  除外 {i}: タイトルが空（sourceUrl={_short(t.get('sourceUrl'))}）")
            continue
        if not url.startswith(("https://", "http://")):
            log(f"  除外 {i}: 出典が http(s) の URL でない（title={_short(title)}, sourceUrl={_short(t.get('sourceUrl'))}）")
            continue
        try:
            importance = int(t.get("importance", 0))
        except (TypeError, ValueError):
            importance = 0
        topics.append({
            "title": title,
            "summary": _str(t.get("summary")),
            "sourceUrl": url,
            "importance": max(1, min(10, importance)),
            "reason": _str(t.get("reason")),
        })
    return topics


def validate_article(data: object) -> dict:
    """記事の応答を検証する。タイトル・本文・参考情報が空、または用語解説が 0 件なら ValueError。"""
    if not isinstance(data, dict):
        raise ValueError("記事の応答の形が不正です")
    article = {
        "title": _str(data.get("title")),
        "slug": _str(data.get("slug")),
        "description": _str(data.get("description")),
        "tags": [_str(t) for t in data.get("tags", []) if _str(t)] if isinstance(data.get("tags"), list) else [],
        "body": _str(data.get("body")),
        "background": _str(data.get("background")),
        "glossary": [
            {"term": _str(g.get("term")), "description": _str(g.get("description"))}
            for g in (data.get("glossary") if isinstance(data.get("glossary"), list) else [])
            if isinstance(g, dict) and _str(g.get("term")) and _str(g.get("description"))
        ],
    }
    for key in ("title", "body", "background"):
        if not article[key]:
            raise ValueError(f"記事の {key} が空です")
    if not article["glossary"]:
        raise ValueError("記事の用語解説が 0 件です")
    return article
