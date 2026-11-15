"""セキュリティ記事の題材選定と記事執筆のプロンプト・JSON スキーマ・応答の検証。

題材の検証は IT ニュースと同じ（it_news.prompts.validate_topics）。
"""

from __future__ import annotations

from it_news.prompts import MAX_TOPICS, TOPICS_SCHEMA, _str

# プロンプトは英語にする（検索クエリが英語になり、英語の一次情報に当たりやすくなる）。出力は日本語に指定する
SYSTEM = (
    "You are a security journalist covering software vulnerabilities and security incidents. "
    "Base every fact on the search results, and never present speculation or unverified information as fact "
    "(for example, do not invent CVE IDs, CVSS scores, affected versions or fixed versions). "
    "Write all output text in Japanese."
)

# 記事の節（JSON のキー）。見出しの順序は security_news.markdown.SECTIONS で決める
TEXT_FIELDS = ("overview", "details", "mitigation", "history", "relatedTech", "notes")
# 空なら記事を書き出さない節。備考（notes）は書くことがなければ空でよい（md では決まった文にする）
REQUIRED_TEXT_FIELDS = tuple(k for k in TEXT_FIELDS if k != "notes")

ARTICLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "slug": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        **{key: {"type": "string"} for key in TEXT_FIELDS},
        "glossary": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"term": {"type": "string"}, "description": {"type": "string"}},
                "required": ["term", "description"],
            },
        },
    },
    "required": ["title", "slug", "description", "tags", *TEXT_FIELDS, "glossary"],
}


def topics_request(recent_titles: list[str]) -> tuple[list[dict], dict]:
    covered = "\n".join(f"- {t}" for t in recent_titles) or "(none)"
    user = (
        f"List up to {MAX_TOPICS} important security vulnerabilities or security incidents "
        "disclosed or updated in the last 24-48 hours.\n"
        "- Prefer vulnerabilities in widely used software, services, libraries, operating systems and devices.\n"
        "- importance: an integer from 1 to 10, ranked by severity (CVSS), whether it is actively exploited "
        "(for example listed in the CISA KEV catalog), and the number of affected users or systems.\n"
        "- sourceUrl: the URL of the primary source (vendor security advisory, NVD, JVN, JPCERT/CC, CISA, "
        "or a reputable security news outlet).\n"
        "- title, summary, reason: write these in Japanese.\n"
        "Exclude topics already covered by the following articles (titles are in Japanese).\n"
        f"{covered}"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], TOPICS_SCHEMA


def article_request(topic: dict) -> tuple[list[dict], dict]:
    user = (
        "Write a security article about the following vulnerability or security incident. "
        "Write every field in Japanese, except slug, CVE IDs and the names of technologies and products.\n"
        f"Topic: {topic['title']}\nSummary: {topic['summary']}\nSource: {topic['sourceUrl']}\n\n"
        "Every Markdown field must not use HTML tags or # / ## headings (use ### or lower if needed), "
        "and should add a citation number such as [1] to each sentence based on the search results.\n"
        "- title: the article title (at most 60 Japanese characters)\n"
        "- slug: a short string of lowercase English letters, digits and hyphens describing the content "
        "(e.g. cve-2026-12345-openssl)\n"
        "- description: a summary in one or two sentences\n"
        "- tags: 1 to 5 related product names, technologies or CVE IDs\n"
        "- overview: Markdown. What happened, who is affected and how serious it is (200-400 Japanese characters)\n"
        "- details: Markdown. The technical details of the vulnerability: CVE IDs, CVSS score, affected products and "
        "versions, the attack vector and conditions, and whether it is exploited in the wild\n"
        "- mitigation: Markdown. Concrete steps to respond: fixed versions to update to, workarounds, "
        "configuration changes, and how to check whether you are affected or compromised\n"
        "- history: Markdown. How the IT industry got here: the discovery and disclosure timeline, "
        "similar past vulnerabilities or incidents, and how the industry responded\n"
        "- relatedTech: Markdown. Related technologies, protocols and standards needed to understand this topic\n"
        "- glossary: 2 to 6 technical terms used in the article, each with a short explanation for beginners\n"
        "- notes: Markdown. Remarks: unconfirmed or still-changing information (for example CVSS not yet assigned, "
        "patch not yet released), the point in time the information is based on, and other caveats\n"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], ARTICLE_SCHEMA


def validate_article(data: object) -> dict:
    """記事の応答を検証する。タイトル・備考以外の節が空、または用語解説が 0 件なら ValueError。"""
    if not isinstance(data, dict):
        raise ValueError("記事の応答の形が不正です")
    tags = data.get("tags")
    glossary = data.get("glossary")
    article = {
        "title": _str(data.get("title")),
        "slug": _str(data.get("slug")),
        "description": _str(data.get("description")),
        "tags": [_str(t) for t in tags if _str(t)] if isinstance(tags, list) else [],
        **{key: _str(data.get(key)) for key in TEXT_FIELDS},
        "glossary": [
            {"term": _str(g.get("term")), "description": _str(g.get("description"))}
            for g in (glossary if isinstance(glossary, list) else [])
            if isinstance(g, dict) and _str(g.get("term")) and _str(g.get("description"))
        ],
    }
    for key in ("title", *REQUIRED_TEXT_FIELDS):
        if not article[key]:
            raise ValueError(f"記事の {key} が空です")
    if not article["glossary"]:
        raise ValueError("記事の用語解説が 0 件です")
    return article
