import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

import generate_security_articles
from it_news.generate import run_generation
from security_news import SECURITY_NEWS
from security_news.markdown import SECTIONS, build_security_markdown
from security_news.prompts import ARTICLE_SCHEMA, article_request, topics_request, validate_article
from tests.fakes import FakePost, response

NOW = datetime(2026, 11, 14, 1, 0, tzinfo=timezone.utc)
REFS = [{"title": "Advisory", "url": "https://vendor.example.com/advisory/1"}]
HEADINGS = ["概要", "脆弱性の詳細", "具体的な対応方法", "IT業界における経緯", "関連技術", "IT用語の解説", "備考", "参考リンク"]


def sec_article(slug="cve-2026-0001", **over):
    a = {
        "title": "製品 X に深刻な脆弱性",
        "slug": slug,
        "description": "製品 X にリモートでコードを実行される脆弱性が見つかった。",
        "tags": ["製品 X", "CVE-2026-0001"],
        "overview": "概要の文 [1]",
        "details": "詳細の文 [1]",
        "mitigation": "- バージョン 1.2.3 に更新する [1]",
        "history": "経緯の文",
        "relatedTech": "関連技術の文",
        "glossary": [{"term": "RCE", "description": "遠隔からコードを実行されること"}],
        "notes": "CVSS は未確定。",
    }
    a.update(over)
    return a


def topic(title, url, importance):
    return {"title": title, "summary": "s", "sourceUrl": url, "importance": importance, "reason": "r"}


def build(article, refs=REFS):
    return build_security_markdown(article=article, references=refs, date="2026-11-14",
                                   source_url="https://vendor.example.com/advisory/1",
                                   generator="perplexity/sonar", tags=["セキュリティ"])


def frontmatter(md):
    lines = md.split("\n")
    end = lines.index("---", 1)
    return {k: json.loads(v) for k, _, v in (line.partition(": ") for line in lines[1:end])}


def h2s(md):
    return [line[3:] for line in md.split("\n") if line.startswith("## ")]


class SecurityMarkdownTest(unittest.TestCase):
    def test_has_the_sections_in_order(self):
        self.assertEqual([h for h, _ in SECTIONS], HEADINGS[:-1])
        self.assertEqual(h2s(build(validate_article(sec_article()))), HEADINGS)

    def test_writes_frontmatter_notice_glossary_and_references(self):
        md = build(validate_article(sec_article()))
        fm = frontmatter(md)
        self.assertEqual(fm["title"], "製品 X に深刻な脆弱性")
        self.assertEqual(fm["date"], "2026-11-14")
        self.assertEqual(fm["tags"], ["セキュリティ", "製品 X", "CVE-2026-0001"])
        self.assertEqual(fm["sourceUrl"], "https://vendor.example.com/advisory/1")
        self.assertEqual(fm["generator"], "perplexity/sonar")
        self.assertIn("> この記事は AI（perplexity/sonar）が 2026-11-14 に自動で作成しました。", md)
        self.assertIn("- **RCE**: 遠隔からコードを実行されること", md)
        self.assertIn("1. [Advisory](https://vendor.example.com/advisory/1)", md)
        self.assertIn("- バージョン 1.2.3 に更新する \\[1\\]", md)

    def test_sanitizes_every_section(self):
        evil = '<script>alert(1)</script> [x](javascript:alert(1)) ![i](https://e.com/i.png)'
        md = build(validate_article(sec_article(**{k: evil for k in ("overview", "details", "mitigation", "history", "relatedTech", "notes")})))
        self.assertNotIn("<script", md)
        # 角かっこはエスケープされ、リンク・画像にならない
        self.assertNotIn("[x](javascript:", md)
        self.assertIn("\\[x\\](javascript:", md)
        self.assertNotIn("![i](", md)
        self.assertEqual(md.count("&lt;script>"), 6)

    def test_closes_an_unclosed_code_fence_inside_a_section(self):
        md = build(validate_article(sec_article(details="```\ncode", mitigation="<b>x</b>")))
        self.assertIn("&lt;b>", md)
        self.assertEqual(h2s(md), HEADINGS)

    def test_demotes_h1_in_sections(self):
        md = build(validate_article(sec_article(overview="# 見出し")))
        self.assertNotIn("\n# 見出し", md)
        self.assertIn("## 見出し", md)

    def test_demotes_h2_in_sections_so_the_structure_stays(self):
        md = build(validate_article(sec_article(details="## 影響を受けるバージョン\n> ## 引用の見出し\n```\n# コードの中\n```")))
        self.assertEqual(h2s(md), HEADINGS)
        self.assertIn("### 影響を受けるバージョン", md)
        self.assertIn("> ### 引用の見出し", md)
        self.assertIn("\n# コードの中\n", md)  # コードブロックの中は変えない

    def test_writes_a_default_note_when_notes_is_empty(self):
        md = build(validate_article(sec_article(notes="")))
        self.assertEqual(h2s(md), HEADINGS)
        self.assertIn("## 備考\n\n特記事項はありません。\n", md)

    def test_sections_match_the_schema(self):
        from security_news.prompts import TEXT_FIELDS
        self.assertEqual(sorted(k for _, k in SECTIONS), sorted([*TEXT_FIELDS, "glossary"]))

    def test_requires_references(self):
        with self.assertRaises(ValueError):
            build(validate_article(sec_article()), refs=[{"title": "x", "url": "javascript:alert(1)"}])


class ValidateSecurityArticleTest(unittest.TestCase):
    def test_requires_every_section_and_glossary(self):
        for key in ("title", "overview", "details", "mitigation", "history", "relatedTech"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_article(sec_article(**{key: "  "}))
        with self.assertRaises(ValueError):
            validate_article(sec_article(glossary=[{"term": "x", "description": ""}]))
        with self.assertRaises(ValueError):
            validate_article("not a dict")

    def test_schema_requires_every_field(self):
        self.assertEqual(sorted(ARTICLE_SCHEMA["required"]), sorted(ARTICLE_SCHEMA["properties"]))
        for key in ("overview", "details", "mitigation", "history", "relatedTech", "glossary", "notes"):
            self.assertIn(key, ARTICLE_SCHEMA["required"])

    def test_notes_may_be_empty(self):
        self.assertEqual(validate_article(sec_article(notes=" "))["notes"], "")


class SecurityPromptsTest(unittest.TestCase):
    def test_asks_for_security_topics_in_japanese_and_lists_covered_titles(self):
        messages, schema = topics_request(["既存の記事"])
        text = "\n".join(m["content"] for m in messages)
        self.assertIn("vulnerabilit", text)
        self.assertIn("Japanese", text)
        self.assertIn("- 既存の記事", text)
        self.assertIn("topics", schema["properties"])

    def test_article_request_includes_the_topic(self):
        messages, schema = article_request(topic("製品 X の脆弱性", "https://e.com/a", 9))
        self.assertIn("製品 X の脆弱性", messages[-1]["content"])
        self.assertIn("https://e.com/a", messages[-1]["content"])
        self.assertIs(schema, ARTICLE_SCHEMA)


class SecurityGenerationTest(unittest.TestCase):
    def test_writes_security_articles_with_week_and_month_recency(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "2026-11-01-old.md").write_text('---\ntitle: "古い"\ndate: "2026-11-01"\nsourceUrl: "https://e.com/old"\n---\n', encoding="utf-8")
            post = FakePost(
                response({"topics": [topic("既出", "https://e.com/old", 9), topic("新", "https://e.com/new", 8)]}),
                response(sec_article("日本語だけ"), search_results=REFS),
            )
            result = run_generation(post=post, api_key="k", model="sonar", count=3, out_dir=Path(d), existing_dirs=[],
                                    tags=["セキュリティ"], now=NOW, log=lambda m: None, kind=SECURITY_NEWS)
            self.assertEqual([Path(p).name for p in result.written], ["2026-11-14-security-news.md"])
            self.assertEqual(result.skipped, 1)
            self.assertEqual(h2s(Path(result.written[0]).read_text(encoding="utf-8")), HEADINGS)
        self.assertEqual([c["body"]["search_recency_filter"] for c in post.calls], ["week", "month"])


class SecurityCliTest(unittest.TestCase):
    def test_requires_api_key_without_calling_api(self):
        post = FakePost()
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            self.assertEqual(generate_security_articles.main(["--out-dir", d], {}, post=post), 1)
        self.assertEqual(post.calls, [])

    def test_count_0_writes_nothing_and_does_not_call_the_api(self):
        post = FakePost()
        for argv, env in ((["--count", "0"], {}), ([], {"SECURITY_ARTICLES_PER_RUN": "0"})):
            with self.subTest(argv=argv), tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
                self.assertEqual(generate_security_articles.main(["--out-dir", d, *argv], {"PERPLEXITY_API_KEY": "k", **env}, post=post), 0)
                self.assertEqual(list(Path(d).glob("*.md")), [])
        self.assertEqual(post.calls, [])
        self.assertEqual(generate_security_articles.resolve_count(None, {"SECURITY_ARTICLES_PER_RUN": "-5"}), 0)

    def test_default_count_and_env(self):
        self.assertEqual(generate_security_articles.resolve_count(None, {}), 3)
        self.assertEqual(generate_security_articles.resolve_count(None, {"SECURITY_ARTICLES_PER_RUN": "6"}), 6)
        self.assertEqual(generate_security_articles.resolve_count(None, {"IT_ARTICLES_PER_RUN": "6"}), 3)

    def test_writes_with_the_default_tag_and_hides_the_key(self):
        post = FakePost(response({"topics": [topic("A", "https://e.com/a", 9)]}), response(sec_article("a"), search_results=REFS))
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as d, redirect_stdout(out):
            code = generate_security_articles.main(["--out-dir", d, "--count", "1"], {"PERPLEXITY_API_KEY": "secret-123"}, post=post)
            self.assertEqual(code, 0)
            fm = frontmatter(next(Path(d).glob("*.md")).read_text(encoding="utf-8"))
        self.assertEqual(fm["tags"][0], "セキュリティ")
        self.assertNotIn("secret-123", out.getvalue())


if __name__ == "__main__":
    unittest.main()
