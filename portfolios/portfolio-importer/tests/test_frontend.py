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
        registered, warnings, _ = register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj")
        self.assertTrue(registered)
        self.assertEqual(warnings, [])
        self.assertTrue((self.apps / "my-app/index.html").is_file())
        self.assertFalse((self.apps / "my-app/dist").exists())
        self.assertEqual(self.manifest(), {"apps": [
            {"slug": "my-app", "outputDir": "dist", "buildArgs": ["--base=/apps/my-app/"]}]})

    def test_appends_to_existing_manifest_once(self):
        write_json(self.apps / "apps.json", {"apps": [{"slug": "a", "outputDir": "dist", "buildArgs": []}]})
        register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj")
        registered, warnings, _ = register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj")
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
        registered, warnings, _ = register_frontend(fe, "my-app", self.repo, self.tmp / "proj")
        self.assertFalse(registered)
        self.assertEqual(warnings, ["フロントエンドを配信登録しませんでした: 静的出力できません"])
        self.assertFalse(self.apps.exists())

    def test_writes_env_on_new_registration(self):
        env = {"VITE_API_URL": "https://api.example.com"}
        _, _, out = register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj", env=env)
        self.assertEqual(out, env)
        self.assertEqual(self.manifest()["apps"][0]["env"], env)

    def test_empty_env_is_not_written(self):
        _, _, out = register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj", env={})
        self.assertEqual(out, {})
        self.assertNotIn("env", self.manifest()["apps"][0])

    def test_adds_missing_env_to_registered_app(self):
        write_json(self.apps / "apps.json", {"apps": [{"slug": "my-app", "outputDir": "dist", "buildArgs": [],
                                                        "env": {"VITE_OTHER_API_URL": "https://o.example.com"}}]})
        _, warnings, out = register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj",
                                             env={"VITE_API_URL": "https://api.example.com"})
        expected = {"VITE_OTHER_API_URL": "https://o.example.com", "VITE_API_URL": "https://api.example.com"}
        self.assertEqual(out, expected)
        self.assertEqual(self.manifest()["apps"][0]["env"], expected)
        self.assertFalse(any("VITE_API_URL" in w for w in warnings))

    def test_registered_app_without_env_gets_env(self):
        write_json(self.apps / "apps.json", {"apps": [{"slug": "my-app", "outputDir": "dist", "buildArgs": []}]})
        _, _, out = register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj",
                                      env={"VITE_API_URL": "https://api.example.com"})
        self.assertEqual(self.manifest()["apps"][0]["env"], {"VITE_API_URL": "https://api.example.com"})
        self.assertEqual(out, {"VITE_API_URL": "https://api.example.com"})

    def test_conflicting_env_is_not_changed(self):
        entry = {"slug": "my-app", "outputDir": "dist", "buildArgs": [], "env": {"VITE_API_URL": "https://old.example.com"}}
        write_json(self.apps / "apps.json", {"apps": [entry]})
        _, warnings, out = register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj",
                                             env={"VITE_API_URL": "https://new.example.com"})
        self.assertEqual(out, {"VITE_API_URL": "https://old.example.com"})
        self.assertEqual(self.manifest()["apps"][0], entry)
        self.assertTrue(any("VITE_API_URL" in w and "変更しませんでした" in w for w in warnings))

    def test_same_env_value_is_silent_and_not_rewritten(self):
        entry = {"slug": "my-app", "outputDir": "dist", "buildArgs": [], "env": {"VITE_API_URL": "https://a.example.com"}}
        write_json(self.apps / "apps.json", {"apps": [entry]})
        before = (self.apps / "apps.json").read_text(encoding="utf-8")
        _, warnings, _ = register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj",
                                           env={"VITE_API_URL": "https://a.example.com"})
        self.assertEqual((self.apps / "apps.json").read_text(encoding="utf-8"), before)
        self.assertFalse(any("VITE_API_URL" in w for w in warnings))

    def test_invalid_existing_env_is_left_alone(self):
        entry = {"slug": "my-app", "outputDir": "dist", "buildArgs": [], "env": ["x"]}
        write_json(self.apps / "apps.json", {"apps": [entry]})
        _, warnings, out = register_frontend(self.fe, "my-app", self.repo, self.tmp / "proj",
                                             env={"VITE_API_URL": "https://a.example.com"})
        self.assertEqual(self.manifest()["apps"][0], entry)
        self.assertEqual(out, {})
        self.assertTrue(any("env" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
