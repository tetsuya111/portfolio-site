import json
import unittest

from importer.detect import Frontend
from importer.frontend import register_frontend
from tests.helpers import TempDirMixin, write, write_json


class RegisterFrontendTest(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.src = self.tmp / "proj/frontend"
        write(self.src / "index.html", "<p>hi</p>")
        write(self.src / ".gitignore", "dist/\n")
        write(self.src / "dist/old.js")
        self.repo = self.tmp / "repo"
        self.apps = self.repo / "portfolio-site/apps"
        self.fe = Frontend(self.src, "vite", "dist", ["--base=/apps/my-app/"])

    def manifest(self):
        return json.loads((self.apps / "apps.json").read_text(encoding="utf-8"))

    def test_copies_source_and_creates_manifest(self):
        registered, warnings = register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj")
        self.assertTrue(registered)
        self.assertEqual(warnings, [])
        self.assertTrue((self.apps / "my-app/index.html").is_file())
        self.assertFalse((self.apps / "my-app/dist").exists())
        self.assertEqual(self.manifest(), {"apps": [
            {"slug": "my-app", "outputDir": "dist", "buildArgs": ["--base=/apps/my-app/"]}]})

    def test_appends_to_existing_manifest_once(self):
        write_json(self.apps / "apps.json", {"apps": [{"slug": "a", "outputDir": "dist", "buildArgs": []}]})
        register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj")
        registered, warnings = register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj")
        self.assertTrue(registered)
        self.assertEqual([a["slug"] for a in self.manifest()["apps"]], ["a", "my-app"])
        self.assertTrue(any("既に" in w for w in warnings))

    def test_existing_app_dir_is_not_overwritten(self):
        write(self.apps / "my-app/index.html", "mine")
        register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj")
        self.assertEqual((self.apps / "my-app/index.html").read_text(encoding="utf-8"), "mine")

    def test_project_root_gitignore_applies_to_frontend_copy(self):
        write(self.tmp / "proj/.gitignore", "node_modules/\n")
        write(self.src / "node_modules/x.js")
        register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj")
        self.assertTrue((self.apps / "my-app/index.html").is_file())
        self.assertFalse((self.apps / "my-app/node_modules").exists())

    def test_root_frontend_copy_excludes_backend_dir(self):
        proj = self.tmp / "rootproj"
        write(proj / "index.html")
        write(proj / "server/app.py")
        fe = Frontend(proj, "vite", "dist", [])
        register_frontend(fe, "my-app", self.repo, proj, exclude=[proj / "server"])
        self.assertTrue((self.apps / "my-app/index.html").is_file())
        self.assertFalse((self.apps / "my-app/server").exists())

    def test_undeliverable_frontend_is_skipped_with_reason(self):
        fe = Frontend(self.src, None, None, [], "静的出力できません")
        registered, warnings = register_frontend(fe, "my-app", self.repo, self.tmp / "proj")
        self.assertFalse(registered)
        self.assertEqual(warnings, ["フロントエンドを配信登録しませんでした: 静的出力できません"])
        self.assertFalse(self.apps.exists())


if __name__ == "__main__":
    unittest.main()
