import tempfile
import unittest
from pathlib import Path

from it_news.files import choose_file_name, load_existing, normalize_url


class NormalizeUrlTest(unittest.TestCase):
    def test_treats_trivial_variants_as_equal(self):
        base = normalize_url("https://example.com/news/a")
        for v in ["https://EXAMPLE.com/news/a/", "https://example.com/news/a#top",
                  "https://example.com/news/a?utm_source=x&utm_medium=y", "http://example.com/news/a"]:
            self.assertEqual(normalize_url(v), base, v)

    def test_keeps_meaningful_query(self):
        self.assertNotEqual(normalize_url("https://e.com/?id=1"), normalize_url("https://e.com/?id=2"))


class LoadExistingTest(unittest.TestCase):
    def test_reads_names_source_urls_and_recent_titles(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d, "a"), Path(d, "b")
            a.mkdir()
            b.mkdir()
            (a / "2026-11-01-old.md").write_text('---\ntitle: "古い"\ndate: "2026-11-01"\nsourceUrl: "https://e.com/old/"\n---\n本文', encoding="utf-8")
            (a / "2026-11-10-new.md").write_text("---\ntitle: 新しい\ndate: 2026-11-10\n---\n本文", encoding="utf-8")
            (b / "hello.md").write_text("---\ntitle: 'こんにちは'\ndate: 2026-01-01\n---\n", encoding="utf-8")
            (a / "note.txt").write_text("x", encoding="utf-8")
            ex = load_existing([a, b, Path(d, "missing")])
        self.assertEqual(ex.names, {"2026-11-01-old", "2026-11-10-new", "hello"})
        self.assertEqual(ex.source_urls, {normalize_url("https://e.com/old")})
        self.assertEqual(ex.recent_titles, ["新しい", "古い", "こんにちは"])

    def test_limits_recent_titles(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(40):
                Path(d, f"2026-01-{i:02d}-a.md").write_text(f"---\ntitle: t{i}\ndate: 2026-01-01\n---\n", encoding="utf-8")
            self.assertEqual(len(load_existing([Path(d)]).recent_titles), 30)


class ChooseFileNameTest(unittest.TestCase):
    def test_uses_date_and_slug(self):
        self.assertEqual(choose_file_name("2026-11-14", "astro-7-release", set()), "2026-11-14-astro-7-release")

    def test_falls_back_for_invalid_slug(self):
        self.assertEqual(choose_file_name("2026-11-14", "日本語", set()), "2026-11-14-it-news")
        self.assertEqual(choose_file_name("2026-11-14", "Bad_Slug--x", set()), "2026-11-14-bad-slug-x")

    def test_avoids_taken_names(self):
        taken = {"2026-11-14-a", "2026-11-14-a-2"}
        self.assertEqual(choose_file_name("2026-11-14", "a", taken), "2026-11-14-a-3")

    def test_limits_length(self):
        name = choose_file_name("2026-11-14", "a" * 30 + "-" + "b" * 60, set())
        self.assertLessEqual(len(name), 64)
        self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        long_taken = {name}
        name2 = choose_file_name("2026-11-14", "a" * 30 + "-" + "b" * 60, long_taken)
        self.assertLessEqual(len(name2), 64)
        self.assertTrue(name2.endswith("-2"))


if __name__ == "__main__":
    unittest.main()
