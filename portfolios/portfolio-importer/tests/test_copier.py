import unittest

from importer import PortfolioError
from importer.copier import copy_tree, make_slug, resolve_target, validate_slug
from tests.helpers import TempDirMixin, write


class SlugTest(unittest.TestCase):
    def test_make_slug_normalizes_name(self):
        self.assertEqual(make_slug("My_App 2"), "my-app-2")
        self.assertEqual(make_slug("--Foo..Bar--"), "foo-bar")

    def test_validate_slug_rejects_invalid_and_reserved(self):
        for bad in ["", "A", "a--b", "-a", "日本語", "docs", "docker-images", "portfolio-importer", "x" * 65]:
            with self.subTest(bad=bad), self.assertRaises(PortfolioError):
                validate_slug(bad)
        validate_slug("my-app-2")


class ResolveTargetTest(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "repo"
        (self.repo / "portfolios").mkdir(parents=True)
        self.outside = self.tmp / "My App"
        self.outside.mkdir()

    def test_outside_project_is_copied_to_portfolios_slug(self):
        t = resolve_target(self.outside, self.repo, None)
        self.assertEqual(t.slug, "my-app")
        self.assertEqual(t.project_dir, self.repo / "portfolios" / "my-app")
        self.assertEqual(t.copy_from, self.outside)

    def test_slug_option_overrides_name(self):
        self.assertEqual(resolve_target(self.outside, self.repo, "other").slug, "other")

    def test_project_under_portfolios_is_used_in_place(self):
        (self.repo / "portfolios/x/backend").mkdir(parents=True)
        t = resolve_target(self.repo / "portfolios/x/backend", self.repo, None)
        self.assertEqual((t.slug, t.project_dir, t.copy_from), ("x", self.repo / "portfolios/x", None))

    def test_existing_destination_is_error(self):
        (self.repo / "portfolios/my-app").mkdir()
        with self.assertRaises(PortfolioError):
            resolve_target(self.outside, self.repo, None)

    def test_rejects_repo_root_and_repo_dirs_outside_portfolios_and_files(self):
        (self.repo / "portfolio-site").mkdir()
        f = write(self.tmp / "file.txt")
        for bad in [self.repo, self.tmp, self.repo / "portfolio-site", f, self.tmp / "missing"]:
            with self.subTest(bad=bad), self.assertRaises(PortfolioError):
                resolve_target(bad, self.repo, None)

    def test_rejects_portfolios_dir_itself(self):
        with self.assertRaises(PortfolioError):
            resolve_target(self.repo / "portfolios", self.repo, None)


class CopyTreeTest(TempDirMixin, unittest.TestCase):
    def test_copies_files_except_excluded(self):
        src = self.tmp / "src"
        write(src / ".gitignore", "node_modules/\n")
        write(src / "node_modules/x.js")
        write(src / "app/main.py", "print(1)")
        write(src / "data.sqlite")
        count = copy_tree(src, self.tmp / "dest")
        self.assertEqual(count, 2)
        self.assertEqual((self.tmp / "dest/app/main.py").read_text(encoding="utf-8"), "print(1)")
        self.assertFalse((self.tmp / "dest/node_modules").exists())
        self.assertFalse((self.tmp / "dest/data.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
