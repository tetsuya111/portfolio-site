import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from stackgen.cli import main
from tests.helpers import TempDirMixin, write, write_json


class CliTest(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "repo"
        self.config = write_json(self.repo / "portfolios" / "backend-compose" / "config.json",
                                 {"domain": "api.portfolio.link", "https": True})
        self.stack = self.repo / "portfolios" / "backend-compose" / "stack"
        self.project = self.repo / "portfolios" / "my-app"

    def run_main(self, path, *extra):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main([str(path), *extra], repo_root=self.repo, config_path=self.config, stack_dir=self.stack)
        return code, out.getvalue(), err.getvalue()

    def test_keeps_mock_until_enable_api(self):
        write(self.project / "backend" / "requirements.txt", "")
        apps = self.repo / "portfolio-site" / "apps"
        write_json(apps / "apps.json", {"apps": [{"slug": "my-app", "outputDir": "dist", "buildArgs": [], "mock": True}]})
        write(apps / "my-app" / "src" / "api.ts", "import.meta.env.VITE_API_URL")
        before = (apps / "apps.json").read_text(encoding="utf-8")
        code, out, _ = self.run_main(self.project)
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertIsNone(result["frontendEnv"])
        self.assertTrue(any("--enable-api" in w for w in result["warnings"]))
        self.assertEqual((apps / "apps.json").read_text(encoding="utf-8"), before)

    def run_args(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args), repo_root=self.repo, config_path=self.config, stack_dir=self.stack)
        return code, out.getvalue(), err.getvalue()

    def test_regenerate_rewrites_stack_from_services_json(self):
        write_json(self.stack / "services.json", {"services": [{"slug": "my-app", "port": 8000}]})
        code, out, _ = self.run_args("--regenerate")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"services": ["my-app"], "https": True, "warnings": []})
        self.assertIn("build: ./services/my-app", (self.stack / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertTrue((self.stack / "init-cert.sh").exists())
        # ソースのコピーは行わない
        self.assertFalse((self.stack / "services" / "my-app").exists())

    def test_regenerate_rejects_project(self):
        code, _, err = self.run_args(str(self.project), "--regenerate")
        self.assertEqual(code, 1)
        self.assertIn("--regenerate", err)

    def test_regenerate_rejects_enable_api(self):
        code, _, err = self.run_args("--regenerate", "--enable-api")
        self.assertEqual(code, 1)
        self.assertIn("--enable-api", err)

    def test_regenerate_warns_scheme_mismatch_in_apps_json(self):
        write_json(self.stack / "services.json", {"services": [{"slug": "my-app", "port": 8000}]})
        write_json(self.repo / "portfolio-site" / "apps" / "apps.json", {"apps": [
            {"slug": "my-app", "mock": False, "env": {"VITE_API_URL": "http://api.portfolio.link/my-app/api"}}]})
        code, out, _ = self.run_args("--regenerate")
        self.assertEqual(code, 0)
        warnings = json.loads(out)["warnings"]
        self.assertEqual(len(warnings), 1)
        self.assertIn("my-app", warnings[0])
        self.assertIn("https://api.portfolio.link/my-app", warnings[0])

    def test_requires_project_without_regenerate(self):
        code, _, err = self.run_args()
        self.assertEqual(code, 1)
        self.assertIn("portfolios/<スラッグ>", err)

    def test_rejects_certbot_name(self):
        certbot = self.repo / "portfolios" / "certbot"
        write(certbot / "backend" / "requirements.txt", "")
        code, _, err = self.run_main(certbot)
        self.assertEqual(code, 1)
        self.assertIn("certbot", err)

    def test_rejects_reverse_proxy_name(self):
        nginx = self.repo / "portfolios" / "nginx"
        write(nginx / "backend" / "requirements.txt", "")
        code, _, err = self.run_main(nginx)
        self.assertEqual(code, 1)
        self.assertIn("nginx", err)
        self.assertFalse(self.stack.exists())

    def test_failed_refresh_keeps_previous_source(self):
        from unittest import mock
        write(self.project / "backend" / "requirements.txt", "")
        write(self.project / "backend" / "main.py", "app = FastAPI()\n")
        self.assertEqual(self.run_main(self.project)[0], 0)
        service = self.stack / "services" / "my-app"
        with mock.patch("stackgen.cli.copy_tree", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                self.run_main(self.project)
        self.assertTrue((service / "main.py").is_file())
        self.assertFalse((service.parent / ".my-app.staging").exists())

    def test_registers_python_backend(self):
        write(self.project / "backend" / "requirements.txt", "fastapi\n")
        write(self.project / "backend" / "main.py", "app = FastAPI()\n")
        write(self.project / "backend" / ".env", "SECRET=x\n")
        apps = self.repo / "portfolio-site" / "apps"
        write_json(apps / "apps.json", {"apps": [{"slug": "my-app", "outputDir": "dist", "buildArgs": [], "mock": True}]})
        write(apps / "my-app" / "src" / "api.ts", "import.meta.env.VITE_API_URL")

        code, out, err = self.run_main(self.project, "--enable-api")
        self.assertEqual(code, 0, err)
        result = json.loads(out)
        self.assertEqual(result["slug"], "my-app")
        self.assertEqual(result["service"], "portfolios/backend-compose/stack/services/my-app")
        self.assertEqual(result["port"], 8000)
        self.assertEqual(result["backendUrl"], "https://api.portfolio.link/my-app")
        self.assertEqual(result["dockerfile"], "portfolios/backend-compose/stack/services/my-app/Dockerfile")
        self.assertEqual(result["frontendEnv"], {"VITE_API_URL": "https://api.portfolio.link/my-app"})
        service = self.stack / "services" / "my-app"
        self.assertTrue((service / "main.py").is_file())
        self.assertFalse((service / ".env").exists())
        self.assertIn("build: ./services/my-app", (self.stack / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertIn("location ~ ^/my-app(?:/|$)", (self.stack / "nginx" / "default.conf").read_text(encoding="utf-8"))

    def test_root_backend_excludes_frontend(self):
        write(self.project / "requirements.txt", "flask\n")
        write(self.project / "app.py", "app = Flask(__name__)\n")
        write_json(self.project / "frontend" / "package.json", {"scripts": {"build": "vite build"},
                                                               "devDependencies": {"vite": "1"}})
        code, _, err = self.run_main(self.project)
        self.assertEqual(code, 0, err)
        service = self.stack / "services" / "my-app"
        self.assertTrue((service / "app.py").is_file())
        self.assertFalse((service / "frontend").exists())

    def test_rerun_refreshes_source_and_keeps_dockerfile_and_env(self):
        write(self.project / "backend" / "requirements.txt", "")
        write(self.project / "backend" / "main.py", "app = FastAPI()\n")
        write(self.project / "backend" / "old.py", "")
        self.assertEqual(self.run_main(self.project)[0], 0)
        service = self.stack / "services" / "my-app"
        write(service / "Dockerfile", 'FROM x\nEXPOSE 9000\nCMD ["x"]\n')
        write(service / ".env", "SECRET=x\n")
        write(self.project / "backend" / "main.py", "app = FastAPI()  # v2\n")
        (self.project / "backend" / "old.py").unlink()
        code, out, _ = self.run_main(self.project)
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertTrue(any("入れ直しました" in w for w in result["warnings"]))
        self.assertIn("v2", (service / "main.py").read_text(encoding="utf-8"))
        self.assertFalse((service / "old.py").exists())
        self.assertIn("EXPOSE 9000", (service / "Dockerfile").read_text(encoding="utf-8"))
        self.assertTrue((service / ".env").is_file())
        self.assertEqual(result["port"], 9000)
        services = json.loads((self.stack / "services.json").read_text(encoding="utf-8"))["services"]
        self.assertEqual(len(services), 1)

    def test_errors_write_nothing(self):
        write(self.project / "README.md", "no backend")
        outside = write(self.tmp / "elsewhere" / "backend" / "requirements.txt", "").parent.parent
        nested = write(self.project / "sub" / "backend" / "requirements.txt", "").parent.parent
        for path in (self.project, outside, nested, self.repo / "portfolios" / "backend-compose"):
            with self.subTest(path=path):
                code, _, err = self.run_main(path)
                self.assertEqual(code, 1)
                self.assertIn("エラー", err)
        write(self.project / "backend" / "requirements.txt", "")
        write_json(self.config, {"domain": "api.example.com"})
        self.assertEqual(self.run_main(self.project)[0], 1)
        self.assertFalse(self.stack.exists())

    def test_broken_apps_json_writes_nothing(self):
        write(self.project / "backend" / "requirements.txt", "")
        write(self.repo / "portfolio-site" / "apps" / "apps.json", "{")
        code, _, err = self.run_main(self.project)
        self.assertEqual(code, 1)
        self.assertIn("apps.json", err)
        self.assertFalse(self.stack.exists())
