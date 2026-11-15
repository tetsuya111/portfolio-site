import unittest

from it_news.perplexity import PerplexityError, call_perplexity, extract_json
from it_news.prompts import article_request, topics_request, validate_article, validate_topics
from tests.fakes import FakePost, response

KEY = "pplx-secret-key"


def call(post, **kw):
    args = dict(post=post, api_key=KEY, model="sonar", messages=[{"role": "user", "content": "hi"}],
                schema={"type": "object"}, recency="day")
    args.update(kw)
    return call_perplexity(**args)


class CallTest(unittest.TestCase):
    def test_sends_auth_schema_and_recency(self):
        post = FakePost(response({"a": 1}, search_results=[{"title": "T", "url": "https://e.com"}]))
        call(post, recency="week")
        c = post.calls[0]
        self.assertEqual(c["url"], "https://api.perplexity.ai/chat/completions")
        self.assertEqual(c["headers"]["Authorization"], f"Bearer {KEY}")
        self.assertEqual(c["body"]["model"], "sonar")
        self.assertEqual(c["body"]["response_format"]["type"], "json_schema")
        self.assertEqual(c["body"]["response_format"]["json_schema"]["schema"], {"type": "object"})
        self.assertEqual(c["body"]["search_recency_filter"], "week")

    def test_returns_data_and_search_results_as_references(self):
        data, refs = call(FakePost(response({"a": 1}, search_results=[{"title": "T", "url": "https://e.com", "date": "x"}])))
        self.assertEqual(data, {"a": 1})
        self.assertEqual(refs, [{"title": "T", "url": "https://e.com"}])

    def test_falls_back_to_citations(self):
        _, refs = call(FakePost(response({"a": 1}, citations=["https://e.com/1"])))
        self.assertEqual(refs, [{"title": "https://e.com/1", "url": "https://e.com/1"}])

    def test_http_error_does_not_leak_key(self):
        with self.assertRaises(PerplexityError) as cm:
            call(FakePost((401, f'{{"error": "bad key {KEY}"}}')))
        self.assertIn("401", str(cm.exception))
        self.assertNotIn(KEY, str(cm.exception))

    def test_broken_connection_raises_perplexity_error(self):
        import http.client

        def post(url, headers, body, timeout):
            raise http.client.IncompleteRead(b"partial")

        with self.assertRaises(PerplexityError):
            call(post)

    def test_non_json_content_raises(self):
        with self.assertRaises(PerplexityError):
            call(FakePost(response("すみません、わかりません")))


class ExtractJsonTest(unittest.TestCase):
    def test_strips_fence_and_think(self):
        self.assertEqual(extract_json('<think>考え中</think>\n```json\n{"a": 1}\n```'), {"a": 1})

    def test_plain(self):
        self.assertEqual(extract_json(' {"a": [1]} '), {"a": [1]})


class PromptsTest(unittest.TestCase):
    def test_topics_request_mentions_covered_titles(self):
        messages, schema = topics_request(["既出のタイトル"])
        self.assertIn("既出のタイトル", messages[-1]["content"])
        self.assertEqual(schema["type"], "object")

    def test_prompts_require_japanese_output(self):
        # プロンプトは英語（検索クエリが英語になり一次情報に当たりやすい）、出力は日本語
        topic = {"title": "Astro 7", "summary": "s", "sourceUrl": "https://e.com", "importance": 8, "reason": "r"}
        for messages, _ in (topics_request([]), article_request(topic)):
            self.assertIn("Japanese", messages[0]["content"])
            self.assertIn("Japanese", messages[-1]["content"])

    def test_validate_topics_drops_invalid(self):
        topics = validate_topics({"topics": [
            {"title": "A", "summary": "s", "sourceUrl": "https://e.com/a", "importance": 8, "reason": "r"},
            {"title": "B", "summary": "s", "sourceUrl": "ftp://e.com/b", "importance": 9, "reason": "r"},
            {"title": "", "summary": "s", "sourceUrl": "https://e.com/c", "importance": 5, "reason": "r"},
            {"title": "D", "summary": "s", "sourceUrl": "https://e.com/d", "importance": 99, "reason": "r"},
        ]})
        self.assertEqual([t["title"] for t in topics], ["A", "D"])
        self.assertEqual(topics[1]["importance"], 10)

    def test_validate_topics_logs_received_count_and_drop_reasons(self):
        lines = []
        validate_topics({"topics": [
            {"title": "A", "sourceUrl": "https://e.com/a", "importance": 8},
            {"title": "B", "sourceUrl": "www.e.com/b", "importance": 9},
            {"title": "", "sourceUrl": "https://e.com/c", "importance": 5},
            "not-a-dict",
        ]}, log=lines.append)
        text = "\n".join(lines)
        self.assertIn("4 件", text)
        self.assertIn("www.e.com/b", text)  # 出典が http(s) でない
        self.assertIn("タイトルが空", text)
        self.assertIn("オブジェクトではない", text)
        self.assertNotIn("e.com/a", text)  # 採用した題材は理由を出さない

    def test_validate_topics_logs_empty_array(self):
        lines = []
        self.assertEqual(validate_topics({"topics": []}, log=lines.append), [])
        self.assertIn("0 件", "\n".join(lines))

    def test_validate_topics_rejects_wrong_shape(self):
        with self.assertRaises(ValueError):
            validate_topics({"items": []})

    def test_article_request_includes_topic(self):
        messages, _ = article_request({"title": "Astro 7", "summary": "s", "sourceUrl": "https://e.com", "importance": 8, "reason": "r"})
        self.assertIn("Astro 7", messages[-1]["content"])
        self.assertIn("https://e.com", messages[-1]["content"])

    def test_validate_article(self):
        ok = {"title": "T", "slug": "t", "description": "d", "tags": ["x"], "body": "b", "background": "bg",
              "glossary": [{"term": "a", "description": "b"}]}
        self.assertEqual(validate_article(ok)["title"], "T")
        with self.assertRaises(ValueError):
            validate_article({**ok, "glossary": []})
        with self.assertRaises(ValueError):
            validate_article({**ok, "body": ""})


if __name__ == "__main__":
    unittest.main()
