"""題材選定と記事執筆のプロンプト・JSON スキーマ・応答の検証。"""

from __future__ import annotations

MAX_TOPICS = 15

SYSTEM = (
    "あなたは IT 分野の技術記者です。事実は検索結果に基づいて書き、推測や未確認の情報を事実として書かないでください。"
    "日本語で書いてください。"
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
    covered = "\n".join(f"- {t}" for t in recent_titles) or "（なし）"
    user = (
        f"直近 24〜48 時間に公開された IT・ソフトウェア開発分野のニュースから、重要なものを最大 {MAX_TOPICS} 件挙げてください。\n"
        "importance は 1〜10 の整数で、開発者・IT 業界への影響の大きさ（利用者の多さ、セキュリティ上の深刻さ、標準や主要製品の変化）で比べてください。\n"
        "sourceUrl はそのニュースの一次情報（公式発表・公式ブログ・信頼できる報道）の URL にしてください。\n"
        "次の記事で取り上げ済みの話題は除いてください。\n"
        f"{covered}"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], TOPICS_SCHEMA


def article_request(topic: dict) -> tuple[list[dict], dict]:
    user = (
        "次の IT ニュースについて、技術記事を書いてください。\n"
        f"題材: {topic['title']}\n概要: {topic['summary']}\n出典: {topic['sourceUrl']}\n\n"
        "- title: 記事のタイトル（60 文字以内）\n"
        "- slug: 内容を表す英小文字・数字・ハイフンの短い文字列（例 astro-7-release）\n"
        "- description: 1〜2 文の要約\n"
        "- tags: 関連する技術・製品名を 1〜5 個\n"
        "- body: 本文の Markdown（800〜1500 字。見出しは ## から始める。何が起きたか・技術的な要点・開発者への影響を書く。"
        "検索結果に基づく文には [1] のように出典の番号を付ける。HTML タグは使わない）\n"
        "- background: 参考情報の Markdown（背景・これまでの経緯・関連する技術や動向）\n"
        "- glossary: 本文に出てくる専門用語 2〜6 個と、初学者向けの短い説明\n"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], ARTICLE_SCHEMA


def _str(v: object) -> str:
    return v.strip() if isinstance(v, str) else ""


def validate_topics(data: object) -> list[dict]:
    """形が正しい題材だけを返す（http(s) の出典・空でないタイトル。importance は 1〜10 に丸める）。"""
    if not isinstance(data, dict) or not isinstance(data.get("topics"), list):
        raise ValueError("題材の応答の形が不正です（topics の配列がありません）")
    topics = []
    for t in data["topics"]:
        if not isinstance(t, dict):
            continue
        title, url = _str(t.get("title")), _str(t.get("sourceUrl"))
        if not title or not url.startswith(("https://", "http://")):
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
