import json
import unittest

from it_news.markdown import build_article_markdown, sanitize_markdown

ARTICLE = {
    "title": 'Astro: "7.0" がリリース',
    "description": "Astro の新しいメジャーバージョン",
    "tags": ["Astro", "Web"],
    "body": "## 概要\n\n新しいバージョンが出た[1]。",
    "background": "Astro は静的サイトジェネレーター。",
    "glossary": [{"term": "SSG", "description": "静的サイト生成"}],
}
REFS = [
    {"title": "Astro Blog", "url": "https://astro.build/blog/astro-7/"},
    {"title": "bad", "url": "javascript:alert(1)"},
]


def frontmatter(md: str) -> dict:
    lines = md.split("\n")
    assert lines[0] == "---"
    end = lines.index("---", 1)
    data = {}
    for line in lines[1:end]:
        key, _, value = line.partition(": ")
        data[key] = json.loads(value)
    return data


class SanitizeTest(unittest.TestCase):
    def test_escapes_raw_html(self):
        self.assertEqual(sanitize_markdown("a <script>alert(1)</script>"), "a &lt;script>alert(1)&lt;/script>")

    def test_keeps_html_in_code(self):
        md = "`<b>` と\n\n```html\n<div>x</div>\n```\n"
        self.assertEqual(sanitize_markdown(md), md)

    def test_keeps_only_plain_http_links(self):
        self.assertEqual(
            sanitize_markdown("[x](javascript:alert(1)) [y](https://e.com) [z](#a)"),
            r"\[x\](javascript:alert(1)) [y](https://e.com) [z](#a)",
        )

    def test_neutralizes_link_bypasses(self):
        # どの書き方でも、http(s)・# 以外のリンク先のリンク・画像・参照定義が作れないこと（角かっこをすべてエスケープする）
        for md in [
            "[x](javascript:alert(1) 'a')",
            "[x](javascript:alert((1)))",
            "[a [b] c](javascript:alert(1))",
            "[`click`](javascript:alert(1))",
            "[click\nhere](javascript:alert(1))",
            "[x]: javascript:alert(1)",
            "![x](javascript:alert(1))",
            "[x](&#106;avascript:alert(1))",
            "[x](JaVaScRiPt:alert(1))",
            "[x][r]\n\n[r]: javascript:alert(1)",
        ]:
            out = sanitize_markdown(md)
            self.assertNotRegex(out, r"(?<!\\)[\[\]]", md)

    def test_citation_markers_stay_readable(self):
        self.assertEqual(sanitize_markdown("出た[1]。"), r"出た\[1\]。")

    def test_fence_with_backtick_in_info_is_not_a_fence(self):
        self.assertNotIn("<img", sanitize_markdown("``` `x`\n<img src=x onerror=alert(1)>"))

    def test_fence_closes_only_with_same_char_and_length(self):
        out = sanitize_markdown("````\n```\n<b>code</b>\n````\n<script>x</script>")
        self.assertIn("<b>code</b>", out)
        self.assertNotIn("<script>", out)

    def test_inline_code_needs_matching_backtick_runs(self):
        # `` で始まり ` で閉じるもの・\` で始まるものはコードではないので、中の < はエスケープする
        self.assertNotIn("<img", sanitize_markdown("``a <img src=x onerror=alert(1)> `"))
        self.assertNotIn("<img", sanitize_markdown(r"\`a <img src=x onerror=alert(1)> `"))
        self.assertEqual(sanitize_markdown("``a`b`` と `Array<T>`"), "``a`b`` と `Array<T>`")

    def test_demotes_h1(self):
        self.assertEqual(sanitize_markdown("# 見出し\n## 小見出し"), "## 見出し\n## 小見出し")

    def test_demotes_setext_and_quoted_h1(self):
        self.assertEqual(sanitize_markdown("概要\n===="), "概要\n----")
        self.assertEqual(sanitize_markdown("> # 引用"), "> ## 引用")

    def test_code_span_cannot_continue_from_previous_line(self):
        # 前の行で閉じていない ` があると、次の行の ` はそれを閉じる（CommonMark）。行をまたぐコードを作らせない
        # 行の中で閉じていない ` はエスケープするので、2行目の `…` は2行目の中だけのコードになる（中の < はコードとして表示される）
        out = sanitize_markdown("a `\nb` <img src=x onerror=alert(1)> `c")
        self.assertEqual(out.split("\n"), ["a \\`", "b` <img src=x onerror=alert(1)> `c"])
        self.assertEqual(sanitize_markdown("x ``` y"), "x \\`\\`\\` y")

    def test_fence_inside_list_item_is_not_trusted(self):
        out = sanitize_markdown("- item\n  ```\n<img src=x onerror=alert(1)>")
        self.assertNotIn("<img", out)

    def test_images_are_not_kept(self):
        self.assertNotRegex(sanitize_markdown("![x](https://tracker.example/p.gif)"), r"!\[")


class BuildTest(unittest.TestCase):
    def build(self, **kw):
        args = dict(article=ARTICLE, references=REFS, date="2026-11-14", source_url="https://astro.build/blog/astro-7/",
                    generator="perplexity/sonar", tags=["IT ニュース"])
        args.update(kw)
        return build_article_markdown(**args)

    def test_frontmatter(self):
        fm = frontmatter(self.build())
        self.assertEqual(fm["title"], 'Astro: "7.0" がリリース')
        self.assertEqual(fm["date"], "2026-11-14")
        self.assertEqual(fm["tags"], ["IT ニュース", "Astro", "Web"])
        self.assertEqual(fm["description"], "Astro の新しいメジャーバージョン")
        self.assertEqual(fm["sourceUrl"], "https://astro.build/blog/astro-7/")
        self.assertEqual(fm["generator"], "perplexity/sonar")

    def test_sections_in_order(self):
        md = self.build()
        idx = [md.index(s) for s in ["に自動で作成しました", "## 概要", "## 参考情報", "## 用語解説", "## 参考リンク"]]
        self.assertEqual(idx, sorted(idx))
        self.assertIn("- **SSG**: 静的サイト生成", md)

    def test_references_numbered_and_http_only(self):
        md = self.build()
        self.assertIn("1. [Astro Blog](https://astro.build/blog/astro-7/)", md)
        self.assertNotIn("javascript:", md)

    def test_drops_reference_urls_with_whitespace_or_control_chars(self):
        md = self.build(references=[
            {"title": "bad", "url": "https://x.example/a\n<script>alert(1)</script>"},
            {"title": "tab", "url": "https://x.example/\tb"},
            {"title": "ok", "url": "https://x.example/c(1)"},
        ])
        self.assertNotIn("<script>", md)
        self.assertNotIn("x.example/a", md)
        self.assertIn("1. [ok](https://x.example/c%281%29)", md)

    def test_rejects_without_references(self):
        with self.assertRaises(ValueError):
            self.build(references=[{"title": "x", "url": "ftp://x"}])

    def test_rejects_without_glossary(self):
        with self.assertRaises(ValueError):
            self.build(article={**ARTICLE, "glossary": []})

    def test_rejects_empty_title_or_bad_date(self):
        with self.assertRaises(ValueError):
            self.build(article={**ARTICLE, "title": " "})
        with self.assertRaises(ValueError):
            self.build(date="2026-13-40")

    def test_sanitizes_every_text_section(self):
        md = self.build(article={**ARTICLE, "background": "<img src=x onerror=alert(1)>",
                                 "glossary": [{"term": "<b>", "description": "<i>x</i>"}]})
        self.assertNotIn("<img", md)
        self.assertNotIn("<b>", md)
        self.assertNotIn("<i>", md)


if __name__ == "__main__":
    unittest.main()
