import contextlib
import io
import json
import subprocess
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
        write(self.src / "backend/requirements.txt", "fastapi\n")
        write(self.src / "backend/main.py", "from fastapi import FastAPI\napp = FastAPI()\n")
        write(self.src / "backend/app.sqlite")
        self.calls = []

    def run_main(self, *args):
        def run(argv, **kwargs):
            self.calls.append(argv)
            return subprocess.CompletedProcess(argv, 0)

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(args), repo_root=self.repo, run=run, today=date(2026, 11, 14))
        return code, out.getvalue(), err.getvalue()

    def test_imports_outside_project_end_to_end(self):
        code, out, _ = self.run_main(str(self.src))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["slug"], "my-app")
        self.assertEqual(result["projectDir"], "portfolios/my-app")
        self.assertTrue(result["copied"])
        self.assertEqual(result["frontend"], {"dir": "portfolios/my-app/frontend", "kind": "vite", "registered": True})
        self.assertEqual(result["backend"]["kind"], "python")
        self.assertEqual(result["backend"]["dockerfile"], "portfolios/my-app/backend/Dockerfile")
        self.assertIsNone(result["backend"]["image"])
        self.assertEqual(result["content"], "portfolio-site/src/content/portfolios/my-app.md")
        self.assertFalse((self.repo / "portfolios/my-app/backend/app.sqlite").exists())
        self.assertTrue((self.repo / "portfolio-site/apps/my-app/index.html").is_file())
        md = (self.repo / result["content"]).read_text(encoding="utf-8")
        self.assertIn('  - "FastAPI"', md)
        self.assertIn('  - "Vite"', md)
        self.assertNotIn("url:", md)
        self.assertEqual(self.calls, [])

    def test_site_url_sets_app_url(self):
        self.run_main(str(self.src), "--site-url", "https://ex.com")
        md = (self.repo / "portfolio-site/src/content/portfolios/my-app.md").read_text(encoding="utf-8")
        self.assertIn('url: "https://ex.com/apps/my-app/"', md)

    def test_invalid_site_url_is_error(self):
        code, _, err = self.run_main(str(self.src), "--site-url", "javascript:x")
        self.assertEqual(code, 1)
        self.assertIn("http", err)
        self.assertFalse((self.repo / "portfolios/my-app").exists())

    def test_build_image_runs_docker(self):
        code, out, _ = self.run_main(str(self.src), "--build-image")
        self.assertEqual(code, 0)
        self.assertEqual([c[:2] for c in self.calls], [["docker", "build"], ["docker", "save"]])
        self.assertEqual(json.loads(out)["backend"]["image"], "portfolios/docker-images/my-app-backend.tar")

    def test_build_image_skipped_without_cmd(self):
        (self.src / "backend/main.py").unlink()
        code, out, _ = self.run_main(str(self.src), "--build-image")
        self.assertEqual(code, 0)
        self.assertEqual(self.calls, [])
        self.assertTrue(any("CMD" in w for w in json.loads(out)["warnings"]))

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
