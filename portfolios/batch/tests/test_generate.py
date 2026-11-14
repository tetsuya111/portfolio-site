import io
import json
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

import generate_it_articles
from it_news.generate import jst_date, run_generation
from tests.fakes import FakePost, response

NOW = datetime(2026, 11, 14, 1, 0, tzinfo=timezone.utc)
REFS = [{"title": "Src", "url": "https://src.example.com/a"}]


def topic(title, url, importance):
    return {"title": title, "summary": "s", "sourceUrl": url, "importance": importance, "reason": "r"}


def article(slug):
    return {"title": f"記事 {slug}", "slug": slug, "description": "d", "tags": ["x"], "body": "本文 [1]",
            "background": "背景", "glossary": [{"term": "用語", "description": "説明"}]}


def frontmatter(path):
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    end = lines.index("---", 1)
    return {k: json.loads(v) for k, _, v in (line.partition(": ") for line in lines[1:end])}


class RunGenerationTest(unittest.TestCase):
    def run_with(self, post, out, count=2, existing=()):
        return run_generation(post=post, api_key="k", model="sonar", count=count, out_dir=Path(out),
                              existing_dirs=[Path(d) for d in existing], tags=["IT ニュース"], now=NOW, log=lambda m: None)

    def test_writes_most_important_topics_first(self):
        post = FakePost(
            response({"topics": [topic("低", "https://e.com/low", 3), topic("高", "https://e.com/high", 9), topic("中", "https://e.com/mid", 6)]}),
            response(article("high"), search_results=REFS),
            response(article("mid"), search_results=REFS),
        )
        with tempfile.TemporaryDirectory() as d:
            result = self.run_with(post, d)
            self.assertEqual([Path(p).name for p in result.written], ["2026-11-14-high.md", "2026-11-14-mid.md"])
            fm = frontmatter(result.written[0])
            self.assertEqual(fm["sourceUrl"], "https://e.com/high")
            self.assertEqual(fm["generator"], "perplexity/sonar")
            self.assertEqual(fm["tags"][0], "IT ニュース")
        self.assertIn("高", post.calls[1]["body"]["messages"][-1]["content"])
        self.assertEqual(post.calls[0]["body"]["search_recency_filter"], "day")
        self.assertEqual(post.calls[1]["body"]["search_recency_filter"], "week")

    def test_skips_topics_already_written_or_duplicated(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "2026-11-01-old.md").write_text('---\ntitle: "古い記事"\ndate: "2026-11-01"\nsourceUrl: "https://e.com/old"\n---\n', encoding="utf-8")
            post = FakePost(
                response({"topics": [topic("既出", "https://e.com/old/", 9), topic("新", "https://e.com/new", 5), topic("新2", "https://e.com/new#x", 4)]}),
                response(article("new"), search_results=REFS),
            )
            result = self.run_with(post, d)
            self.assertEqual(len(result.written), 1)
            self.assertEqual(result.skipped, 2)
        self.assertIn("古い記事", post.calls[0]["body"]["messages"][-1]["content"])

    def test_records_failure_and_continues(self):
        post = FakePost(
            response({"topics": [topic("A", "https://e.com/a", 9), topic("B", "https://e.com/b", 8)]}),
            response(article("a"), search_results=[]),  # 参考リンクなし
            response(article("b"), search_results=REFS),
        )
        with tempfile.TemporaryDirectory() as d:
            result = self.run_with(post, d)
            self.assertEqual(len(result.written), 1)
            self.assertEqual(len(result.failed), 1)
            self.assertEqual(sorted(p.name for p in Path(d).glob("*.md")), ["2026-11-14-b.md"])

    def test_does_not_overwrite_existing_names(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as other:
            Path(other, "2026-11-14-a.md").write_text("---\ntitle: x\ndate: 2026-11-14\n---\n", encoding="utf-8")
            post = FakePost(response({"topics": [topic("A", "https://e.com/a", 9)]}), response(article("a"), search_results=REFS))
            result = self.run_with(post, d, existing=[other])
            self.assertEqual(Path(result.written[0]).name, "2026-11-14-a-2.md")

    def test_jst_date(self):
        self.assertEqual(jst_date(datetime(2026, 11, 14, 16, 0, tzinfo=timezone.utc)), "2026-11-15")
        self.assertEqual(jst_date(datetime(2026, 11, 14, 14, 59, tzinfo=timezone.utc)), "2026-11-14")


class CliTest(unittest.TestCase):
    def test_requires_api_key_without_calling_api(self):
        post = FakePost()
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            self.assertEqual(generate_it_articles.main(["--out-dir", d], {}, post=post), 1)
        self.assertEqual(post.calls, [])

    def test_requires_out_dir(self):
        with self.assertRaises(SystemExit) as cm, redirect_stdout(io.StringIO()), unittest.mock.patch("sys.stderr", io.StringIO()):
            generate_it_articles.main([], {"PERPLEXITY_API_KEY": "k"}, post=FakePost())
        self.assertEqual(cm.exception.code, 2)

    def test_count_is_clamped(self):
        self.assertEqual(generate_it_articles.resolve_count(None, {}), 5)
        self.assertEqual(generate_it_articles.resolve_count(None, {"IT_ARTICLES_PER_RUN": "50"}), 10)
        self.assertEqual(generate_it_articles.resolve_count(0, {}), 1)
        self.assertEqual(generate_it_articles.resolve_count(None, {"IT_ARTICLES_PER_RUN": "abc"}), 5)

    def test_exit_code_1_when_every_article_failed(self):
        post = FakePost(response({"topics": [topic("A", "https://e.com/a", 9)]}), response(article("a"), search_results=[]))
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            self.assertEqual(generate_it_articles.main(["--out-dir", d, "--count", "1"], {"PERPLEXITY_API_KEY": "k"}, post=post), 1)

    def test_exit_code_0_and_no_key_in_output(self):
        post = FakePost(response({"topics": [topic("A", "https://e.com/a", 9)]}), response(article("a"), search_results=REFS))
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as d, redirect_stdout(out):
            self.assertEqual(generate_it_articles.main(["--out-dir", d, "--tag", "News"], {"PERPLEXITY_API_KEY": "secret-123"}, post=post), 0)
        self.assertNotIn("secret-123", out.getvalue())


if __name__ == "__main__":
    unittest.main()
