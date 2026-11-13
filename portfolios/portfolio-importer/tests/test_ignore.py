import os
import unittest

from importer.ignore import iter_files
from tests.helpers import TempDirMixin, write


class IterFilesTest(TempDirMixin, unittest.TestCase):
    def files(self):
        return sorted(p.as_posix() for p in iter_files(self.tmp))

    def test_basename_pattern_matches_at_any_depth(self):
        write(self.tmp / ".gitignore", "*.log\n")
        write(self.tmp / "a.log")
        write(self.tmp / "sub/b.log")
        write(self.tmp / "sub/c.txt")
        self.assertEqual(self.files(), [".gitignore", "sub/c.txt"])

    def test_leading_slash_anchors_to_gitignore_dir(self):
        write(self.tmp / ".gitignore", "/build\n")
        write(self.tmp / "build/x.js")
        write(self.tmp / "src/build/y.js")
        self.assertEqual(self.files(), [".gitignore", "src/build/y.js"])

    def test_trailing_slash_matches_directories_only(self):
        write(self.tmp / ".gitignore", "data/\n")
        write(self.tmp / "data/x.csv")
        write(self.tmp / "sub/data")
        self.assertEqual(self.files(), [".gitignore", "sub/data"])

    def test_negation_reincludes_file(self):
        write(self.tmp / ".gitignore", "*.log\n!keep.log\n")
        write(self.tmp / "a.log")
        write(self.tmp / "keep.log")
        self.assertEqual(self.files(), [".gitignore", "keep.log"])

    def test_negation_cannot_reinclude_inside_excluded_dir(self):
        write(self.tmp / ".gitignore", "out/\n!out/keep.txt\n")
        write(self.tmp / "out/keep.txt")
        self.assertEqual(self.files(), [".gitignore"])

    def test_double_star_matches_any_depth(self):
        write(self.tmp / ".gitignore", "a/**/b\n# comment\n\n")
        write(self.tmp / "a/b")
        write(self.tmp / "a/x/y/b")
        write(self.tmp / "a/c")
        self.assertEqual(self.files(), [".gitignore", "a/c"])

    def test_nested_gitignore_applies_only_below_it(self):
        write(self.tmp / "sub/.gitignore", "*.tmp\n")
        write(self.tmp / "sub/a.tmp")
        write(self.tmp / "b.tmp")
        self.assertEqual(self.files(), ["b.tmp", "sub/.gitignore"])

    def test_always_excludes_vcs_data_and_env(self):
        for name in [".git/HEAD", "x.sqlite", "d/y.sqlite3", "z.db", "z.db-wal", "z.sqlite-journal",
                     ".env", ".env.local", "be/.env"]:
            write(self.tmp / name)
        write(self.tmp / ".env.example")
        self.assertEqual(self.files(), [".env.example"])

    def test_gitignore_negation_does_not_reinclude_always_excluded(self):
        write(self.tmp / ".gitignore", "!*.db\n")
        write(self.tmp / "z.db")
        self.assertEqual(self.files(), [".gitignore"])

    def test_always_excludes_dependency_dirs_and_secret_files(self):
        for name in ["node_modules/a.js", ".venv/lib/x.py", "venv/x", "be/__pycache__/x.pyc", "key.pem", "k.key",
                     ".npmrc", "credentials.json", "credentials-prod.json", "x.pyc", "id_rsa", "id_ed25519.pub",
                     "secrets.yaml", "secrets.json", "secrets.toml", "service-account-prod.json", "a.jks", "a.keystore",
                     "a.secret"]:
            write(self.tmp / name)
        write(self.tmp / "src/keep.txt")
        self.assertEqual(self.files(), ["src/keep.txt"])

    def test_subdirectory_walk_applies_parent_gitignore(self):
        write(self.tmp / ".gitignore", ".next/\n*.log\n")
        write(self.tmp / "frontend/.next/x.js")
        write(self.tmp / "frontend/a.log")
        write(self.tmp / "frontend/index.html")
        self.assertEqual([p.as_posix() for p in iter_files(self.tmp, "frontend")], ["index.html"])

    def test_dot_subdirectory_does_not_duplicate_rules(self):
        write(self.tmp / ".gitignore", "*.log\n!keep.log\n")
        write(self.tmp / "keep.log")
        self.assertEqual([p.as_posix() for p in iter_files(self.tmp, ".")], [".gitignore", "keep.log"])

    def test_skip_dirs_are_not_walked(self):
        write(self.tmp / "index.html")
        write(self.tmp / "server/app.py")
        self.assertEqual([p.as_posix() for p in iter_files(self.tmp, "", skip_dirs={"server"})], ["index.html"])

    def test_source_files_named_secrets_are_kept(self):
        write(self.tmp / "src/lib/secrets.ts")
        write(self.tmp / "config/secrets.py")
        self.assertEqual(self.files(), ["config/secrets.py", "src/lib/secrets.ts"])

    def test_skips_symlinks(self):
        write(self.tmp / "real.txt")
        try:
            os.symlink(self.tmp / "real.txt", self.tmp / "link.txt")
        except (OSError, NotImplementedError):
            self.skipTest("シンボリックリンクを作れない環境")
        self.assertEqual(self.files(), ["real.txt"])


if __name__ == "__main__":
    unittest.main()
