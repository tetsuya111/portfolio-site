import contextlib
import io
import json
import subprocess
import unittest
from datetime import date

from importer.cli import main
from tests.helpers import TempDirMixin, write, write_json


class CliBase(TempDirMixin):
    """取り込み元のプロジェクトと main の呼び出しを用意する。"""

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


class CliTest(CliBase, unittest.TestCase):
    def test_imports_outside_project_end_to_end(self):
        code, out, _ = self.run_main(str(self.src))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["slug"], "my-app")
        self.assertEqual(result["projectDir"], "portfolios/my-app")
        self.assertTrue(result["copied"])
        self.assertEqual(result["frontend"], {"dir": "portfolios/my-app/frontend", "kind": "vite", "registered": True,
                                              "env": {}})
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

    def test_warns_when_frontend_and_backend_share_root(self):
        root = self.tmp / "same"
        write_json(root / "package.json", {"scripts": {"build": "vite build"}, "devDependencies": {"vite": "1"}})
        write(root / "package-lock.json", "{}")
        write(root / "requirements.txt", "fastapi\n")
        write(root / "main.py", "")
        code, out, _ = self.run_main(str(root))
        self.assertEqual(code, 0)
        self.assertTrue(any("同じディレクトリ" in w for w in json.loads(out)["warnings"]))

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


class CliUrlTest(CliBase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        write(self.src / "frontend/src/api.ts", "export const base = import.meta.env.VITE_API_URL;\n")
        write(self.src / "backend/config.py", 'import os\nurl = os.getenv("CORS_ORIGIN")\n')

    def apps(self):
        return json.loads((self.repo / "portfolio-site/apps/apps.json").read_text(encoding="utf-8"))["apps"]

    def dockerfile(self):
        return (self.repo / "portfolios/my-app/backend/Dockerfile").read_text(encoding="utf-8")

    def write_params(self, domain="portfolio.example.com"):
        write_json(self.repo / "portfolio-site/infra/parameters.json", {"Parameters": {"DomainName": domain}})

    def test_invalid_backend_url_is_error(self):
        for bad in ["http://api.example.com", "https://a.example.com/?x=1"]:
            code, _, err = self.run_main(str(self.src), "--backend-url", bad)
            self.assertEqual(code, 1)
            self.assertIn("--backend-url", err)
        self.assertFalse((self.repo / "portfolios/my-app").exists())

    def test_backend_url_is_written_to_apps_json(self):
        code, out, _ = self.run_main(str(self.src), "--backend-url", "https://api.example.com")
        self.assertEqual(code, 0)
        self.assertEqual(self.apps()[0]["env"], {"VITE_API_URL": "https://api.example.com"})
        self.assertEqual(json.loads(out)["frontend"]["env"], {"VITE_API_URL": "https://api.example.com"})

    def test_other_candidate_names_are_warned(self):
        write(self.src / "frontend/src/b.ts", "import.meta.env.VITE_BACKEND_URL\n")
        _, out, _ = self.run_main(str(self.src), "--backend-url", "https://api.example.com")
        self.assertEqual(self.apps()[0]["env"], {"VITE_API_URL": "https://api.example.com"})
        self.assertTrue(any("VITE_BACKEND_URL" in w for w in json.loads(out)["warnings"]))

    def test_backend_url_without_name_warns(self):
        (self.src / "frontend/src/api.ts").unlink()
        _, out, _ = self.run_main(str(self.src), "--backend-url", "https://api.example.com")
        self.assertNotIn("env", self.apps()[0])
        self.assertTrue(any("--backend-url" in w for w in json.loads(out)["warnings"]))

    def test_name_without_backend_url_is_suggested(self):
        _, out, _ = self.run_main(str(self.src))
        self.assertNotIn("env", self.apps()[0])
        self.assertTrue(any("VITE_API_URL" in w for w in json.loads(out)["warnings"]))

    def test_backend_url_added_on_rerun(self):
        self.run_main(str(self.src))
        self.run_main(str(self.repo / "portfolios/my-app"), "--backend-url", "https://api.example.com")
        self.assertEqual(self.apps()[0]["env"], {"VITE_API_URL": "https://api.example.com"})

    def test_domain_name_sets_dockerfile_env_and_md_url(self):
        self.write_params()
        _, out, _ = self.run_main(str(self.src))
        self.assertIn('ENV CORS_ORIGIN="https://portfolio.example.com"\n', self.dockerfile())
        self.assertEqual(json.loads(out)["backend"]["env"], {"CORS_ORIGIN": "https://portfolio.example.com"})
        md = (self.repo / "portfolio-site/src/content/portfolios/my-app.md").read_text(encoding="utf-8")
        self.assertIn('url: "https://portfolio.example.com/apps/my-app/"', md)

    def test_default_backend_name_is_frontend_url(self):
        (self.src / "backend/config.py").unlink()
        self.write_params()
        _, out, _ = self.run_main(str(self.src))
        self.assertIn('ENV FRONTEND_URL="https://portfolio.example.com/apps/my-app/"\n', self.dockerfile())
        self.assertTrue(any("FRONTEND_URL" in w for w in json.loads(out)["warnings"]))

    def test_no_site_url_writes_no_env(self):
        _, out, _ = self.run_main(str(self.src))
        self.assertNotIn("CORS_ORIGIN", self.dockerfile())
        self.assertEqual(json.loads(out)["backend"]["env"], {})
        self.assertTrue(any("parameters.json" in w for w in json.loads(out)["warnings"]))

    def test_site_url_option_wins_over_parameters(self):
        self.write_params()
        self.run_main(str(self.src), "--site-url", "https://other.example.com")
        self.assertIn('ENV CORS_ORIGIN="https://other.example.com"\n', self.dockerfile())


if __name__ == "__main__":
    unittest.main()
