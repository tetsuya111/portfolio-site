import subprocess
import unittest

from importer import PortfolioError
from importer.backend import build_image, write_docker_files
from importer.detect import Backend
from tests.helpers import TempDirMixin, write, write_json


class WriteDockerFilesTest(TempDirMixin, unittest.TestCase):
    def dockerfile(self):
        return (self.tmp / "Dockerfile").read_text(encoding="utf-8")

    def test_uvicorn_command_from_docstring_with_factory(self):
        write(self.tmp / "pyproject.toml", "[project]\n")
        write(self.tmp / "app/main.py", '"""起動: `uvicorn app.main:create_default_app --factory --env-file .env`"""\n')
        r = write_docker_files(Backend(self.tmp, "python"))
        self.assertTrue(r.has_cmd)
        text = self.dockerfile()
        self.assertIn("pip install --no-cache-dir .", text)
        self.assertIn('CMD ["uvicorn", "app.main:create_default_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]', text)
        self.assertIn("USER ", text)
        self.assertTrue((self.tmp / ".dockerignore").is_file())

    def test_uvicorn_command_from_fastapi_assignment(self):
        write(self.tmp / "requirements.txt", "fastapi\n")
        write(self.tmp / "src/server.py", "from fastapi import FastAPI\napi = FastAPI()\n")
        write_docker_files(Backend(self.tmp, "python"))
        text = self.dockerfile()
        self.assertIn("pip install --no-cache-dir -r requirements.txt", text)
        self.assertIn('CMD ["uvicorn", "src.server:api", "--host", "0.0.0.0", "--port", "8000"]', text)

    def test_main_py_fallback(self):
        write(self.tmp / "requirements.txt", "")
        write(self.tmp / "main.py", "print(1)\n")
        write_docker_files(Backend(self.tmp, "python"))
        self.assertIn('CMD ["python", "main.py"]', self.dockerfile())

    def test_node_with_start_script(self):
        write_json(self.tmp / "package.json", {"scripts": {"start": "node ."}})
        write(self.tmp / "package-lock.json", "{}")
        r = write_docker_files(Backend(self.tmp, "node"))
        text = self.dockerfile()
        self.assertTrue(r.has_cmd)
        self.assertIn("npm ci --omit=dev", text)
        self.assertIn('CMD ["npm", "start"]', text)

    def test_node_without_lockfile_uses_install(self):
        write_json(self.tmp / "package.json", {"scripts": {"start": "node ."}})
        write_docker_files(Backend(self.tmp, "node"))
        self.assertIn("npm install --omit=dev", self.dockerfile())

    def test_unknown_command_writes_placeholder_and_warns(self):
        write(self.tmp / "requirements.txt", "")
        r = write_docker_files(Backend(self.tmp, "python"))
        self.assertFalse(r.has_cmd)
        self.assertTrue(r.warnings)
        self.assertNotIn("\nCMD", self.dockerfile())

    def test_existing_files_are_not_overwritten(self):
        write(self.tmp / "requirements.txt", "")
        write(self.tmp / "main.py", "")
        write(self.tmp / "Dockerfile", "FROM scratch\n")
        write(self.tmp / ".dockerignore", "keep\n")
        r = write_docker_files(Backend(self.tmp, "python"))
        self.assertEqual(self.dockerfile(), "FROM scratch\n")
        self.assertEqual((self.tmp / ".dockerignore").read_text(encoding="utf-8"), "keep\n")
        self.assertEqual(len(r.warnings), 3)  # 上書きしない×2 と CMD なし
        self.assertFalse(r.has_cmd)  # 既存の Dockerfile に CMD がない

    def test_existing_dockerfile_with_cmd_counts_as_runnable(self):
        write(self.tmp / "requirements.txt", "")
        write(self.tmp / "Dockerfile", "FROM python\nCMD [\"python\"]\n")
        self.assertTrue(write_docker_files(Backend(self.tmp, "python")).has_cmd)


class BuildImageTest(TempDirMixin, unittest.TestCase):
    def test_runs_docker_build_and_save(self):
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0)

        tar = build_image(self.tmp / "be", "my-app", self.tmp, run=run)
        self.assertEqual(tar, self.tmp / "portfolios/docker-images/my-app-backend.tar")
        self.assertEqual(calls[0], ["docker", "build", "-t", "portfolio-my-app-backend:latest", str(self.tmp / "be")])
        self.assertEqual(calls[1], ["docker", "save", "-o", str(tar), "portfolio-my-app-backend:latest"])
        self.assertIn("*.tar", (self.tmp / "portfolios/docker-images/.gitignore").read_text(encoding="utf-8"))

    def test_docker_failure_raises(self):
        def run(args, **kwargs):
            return subprocess.CompletedProcess(args, 1)

        with self.assertRaises(PortfolioError):
            build_image(self.tmp / "be", "my-app", self.tmp, run=run)

    def test_missing_docker_raises(self):
        def run(args, **kwargs):
            raise FileNotFoundError("docker")

        with self.assertRaises(PortfolioError):
            build_image(self.tmp / "be", "my-app", self.tmp, run=run)


if __name__ == "__main__":
    unittest.main()
