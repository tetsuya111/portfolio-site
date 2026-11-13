import unittest
from datetime import date

from importer.content import parse_frontmatter, write_portfolio_md
from tests.helpers import TempDirMixin, write

TODAY = date(2026, 11, 14)


class ParseFrontmatterTest(unittest.TestCase):
    def test_parses_scalars_and_lists(self):
        data, body = parse_frontmatter('---\ntitle: "A: B"\ntags:\n  - Python\n  - "Next.js"\nurl: ""\n---\n\nbody\n')
        self.assertEqual(data, {"title": "A: B", "tags": ["Python", "Next.js"], "url": ""})
        self.assertEqual(body, "\nbody\n")

    def test_inline_list_and_no_frontmatter(self):
        self.assertEqual(parse_frontmatter("---\ntags: [a, 'b']\n---\n")[0], {"tags": ["a", "b"]})
        self.assertEqual(parse_frontmatter("# x\n"), ({}, "# x\n"))


class WritePortfolioMdTest(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = self.tmp / "portfolios/my-app"
        self.project.mkdir(parents=True)
        self.out = self.tmp / "portfolio-site/src/content/portfolios/my-app.md"

    def call(self, tags=None, app_url=None):
        return write_portfolio_md("my-app", self.project, self.tmp, tags or ["Python"], app_url, TODAY)

    def test_uses_docs_file_and_drops_leading_h1_and_empty_url(self):
        write(self.tmp / "portfolios/docs/my-app.md",
              '---\ntitle: My "App"\ntags:\n  - FastAPI\nurl: ""\n---\n\n# My App\n\n説明\n\n## 機能\n')
        path, warnings = self.call()
        self.assertEqual(path, self.out)
        self.assertEqual(warnings, [])
        self.assertEqual(self.out.read_text(encoding="utf-8"),
                         '---\ntitle: "My \\"App\\""\ntags:\n  - "FastAPI"\ndate: 2026-11-14\n---\n\n説明\n\n## 機能\n')

    def test_falls_back_to_readme(self):
        write(self.project / "README.md", "# Readme Title\n\n本文\n")
        self.call(tags=["Python", "Docker"])
        text = self.out.read_text(encoding="utf-8")
        self.assertTrue(text.startswith('---\ntitle: "Readme Title"\ntags:\n  - "Python"\n  - "Docker"\n'))
        self.assertTrue(text.endswith("---\n\n本文\n"))

    def test_falls_back_to_slug_with_overview_template(self):
        self.call()
        text = self.out.read_text(encoding="utf-8")
        self.assertIn('title: "my-app"', text)
        self.assertIn("## 概要", text)

    def test_app_url_only_when_http(self):
        self.call(app_url="https://example.com/apps/my-app/")
        self.assertIn('url: "https://example.com/apps/my-app/"', self.out.read_text(encoding="utf-8"))

    def test_non_http_url_is_dropped(self):
        write(self.tmp / "portfolios/docs/my-app.md", "---\ntitle: x\nurl: javascript:alert(1)\n---\n")
        self.call()
        self.assertNotIn("url:", self.out.read_text(encoding="utf-8"))

    def test_existing_file_is_not_overwritten(self):
        write(self.out, "mine")
        path, warnings = self.call()
        self.assertIsNone(path)
        self.assertEqual(self.out.read_text(encoding="utf-8"), "mine")
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
