import contextlib
import io
import json
import unittest
from datetime import date

from importer.cli import main
from tests.helpers import TempDirMixin, write, write_json


class CliTest(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "repo"
        (self.repo / "portfolios").mkdir(parents=True)
        self.src = self.tmp / "my-app"
        write(self.src / "README.md", "# My App\n\n説明\n")
        write_json(self.src / "frontend/package.json",
                   {"scripts": {"build": "vite build"}, "devDependencies": {"vite": "1"}})
        write(self.src / "frontend/index.html", "<p>hi</p>")
        write(self.src / "frontend/package-lock.json", "{}")
        write(self.src / "backend/requirements.txt", "fastapi\n")
        write(self.src / "backend/main.py", 'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/api/me")\ndef me(): ...\n')
        write(self.src / "backend/app.sqlite")

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(list(args), repo_root=self.repo, today=date(2026, 11, 14))
            except SystemExit as e:  # argparse の引数エラー
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def test_imports_outside_project_end_to_end(self):
        code, out, _ = self.run_main(str(self.src))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["slug"], "my-app")
        self.assertEqual(result["projectDir"], "portfolios/my-app")
        self.assertTrue(result["copied"])
        self.assertEqual(result["frontend"], {"dir": "portfolios/my-app/frontend", "kind": "vite", "registered": True,
                                              "mock": "portfolio-site/apps/my-app/mock/handlers.js"})
        self.assertEqual(result["backend"], {"dir": "portfolios/my-app/backend", "kind": "python", "routes": 1})
        self.assertFalse((self.repo / "portfolios/my-app/backend/Dockerfile").exists())
        self.assertFalse((self.repo / "portfolios/my-app/backend/.dockerignore").exists())
        handlers = (self.repo / result["frontend"]["mock"]).read_text(encoding="utf-8")
        self.assertIn('portfolioMock.handle("GET", "/api/me"', handlers)
        manifest = json.loads((self.repo / "portfolio-site/apps/apps.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["apps"][0]["mock"])
        self.assertEqual(result["content"], "portfolio-site/src/content/portfolios/my-app.md")
        self.assertFalse((self.repo / "portfolios/my-app/backend/app.sqlite").exists())
        self.assertTrue((self.repo / "portfolio-site/apps/my-app/index.html").is_file())
        md = (self.repo / result["content"]).read_text(encoding="utf-8")
        self.assertIn('  - "FastAPI"', md)
        self.assertIn('  - "Vite"', md)
        self.assertIn('url: "/apps/my-app/"', md)
        self.assertNotIn("Docker", md)

    def test_warns_when_frontend_and_backend_share_root(self):
        root = self.tmp / "same"
        write_json(root / "package.json", {"scripts": {"build": "vite build"}, "devDependencies": {"vite": "1"}})
        write(root / "package-lock.json", "{}")
        write(root / "requirements.txt", "fastapi\n")
        write(root / "main.py", "")
        code, out, _ = self.run_main(str(root))
        self.assertEqual(code, 0)
        self.assertTrue(any("同じディレクトリ" in w for w in json.loads(out)["warnings"]))

    def test_routes_found_when_frontend_is_at_root(self):
        root = self.tmp / "rootfe"
        write_json(root / "package.json", {"scripts": {"build": "vite build"}, "devDependencies": {"vite": "1"}})
        write(root / "package-lock.json", "{}")
        write(root / "backend/requirements.txt", "fastapi\n")
        write(root / "backend/main.py", '@app.get("/api/me")\n')
        code, out, _ = self.run_main(str(root))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["backend"]["routes"], 1)

    def test_site_url_sets_app_url(self):
        self.run_main(str(self.src), "--site-url", "https://ex.com")
        md = (self.repo / "portfolio-site/src/content/portfolios/my-app.md").read_text(encoding="utf-8")
        self.assertIn('url: "https://ex.com/apps/my-app/"', md)

    def test_registered_frontend_gets_relative_url_without_site_url(self):
        self.run_main(str(self.src))
        md = (self.repo / "portfolio-site/src/content/portfolios/my-app.md").read_text(encoding="utf-8")
        self.assertIn('url: "/apps/my-app/"', md)

    def test_no_relative_url_when_frontend_not_registered(self):
        src = self.tmp / "api-only"
        write(src / "README.md", "# API\n")
        write(src / "requirements.txt", "fastapi\n")
        write(src / "main.py", '@app.get("/api/me")\n')
        code, out, _ = self.run_main(str(src))
        self.assertEqual(code, 0)
        md = (self.repo / json.loads(out)["content"]).read_text(encoding="utf-8")
        self.assertNotIn("url:", md)

    def test_invalid_site_url_is_error(self):
        code, _, err = self.run_main(str(self.src), "--site-url", "javascript:x")
        self.assertEqual(code, 1)
        self.assertIn("http", err)
        self.assertFalse((self.repo / "portfolios/my-app").exists())

    def test_build_image_option_is_removed(self):
        code, _, err = self.run_main(str(self.src), "--build-image")
        self.assertEqual(code, 2)
        self.assertIn("--build-image", err)
        self.assertFalse((self.repo / "portfolios/my-app").exists())

    def test_no_mock_without_backend(self):
        import shutil
        shutil.rmtree(self.src / "backend")
        code, out, _ = self.run_main(str(self.src))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertIsNone(result["backend"])
        self.assertIsNone(result["frontend"]["mock"])
        self.assertFalse((self.repo / "portfolio-site/apps/my-app/mock").exists())
        manifest = json.loads((self.repo / "portfolio-site/apps/apps.json").read_text(encoding="utf-8"))
        self.assertNotIn("mock", manifest["apps"][0])

    def test_no_mock_when_frontend_not_registered(self):
        (self.src / "frontend/package-lock.json").unlink()
        code, out, _ = self.run_main(str(self.src))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertFalse(result["frontend"]["registered"])
        self.assertIsNone(result["frontend"]["mock"])
        self.assertEqual(result["backend"]["routes"], 1)

    def test_rerun_in_place_does_not_copy(self):
        self.run_main(str(self.src))
        code, out, _ = self.run_main(str(self.repo / "portfolios/my-app"))
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out)["copied"])

    def test_error_exits_with_1(self):
        self.run_main(str(self.src))
        code, out, err = self.run_main(str(self.src))
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("既に存在", err)


if __name__ == "__main__":
    unittest.main()
