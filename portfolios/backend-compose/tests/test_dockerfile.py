import unittest

from stackgen.dockerfile import detect_port, write_docker_files
from tests.helpers import TempDirMixin, write, write_json


class WriteDockerFilesTest(TempDirMixin, unittest.TestCase):
    def dockerfile(self, kind="python"):
        path, warnings = write_docker_files(self.tmp, kind)
        return path.read_text(encoding="utf-8"), warnings

    def test_fastapi_assignment(self):
        write(self.tmp / "requirements.txt", "fastapi\nuvicorn\n")
        write(self.tmp / "main.py", "from fastapi import FastAPI\napp = FastAPI()\n")
        text, warnings = self.dockerfile()
        self.assertIn('CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]', text)
        self.assertIn("pip install --no-cache-dir -r requirements.txt", text)
        # 依存に uvicorn がなくても起動できるよう入れる
        self.assertIn("pip install --no-cache-dir uvicorn", text)
        self.assertEqual(warnings, [])
        self.assertTrue((self.tmp / ".dockerignore").is_file())

    def test_readme_uvicorn_command_wins(self):
        write(self.tmp / "pyproject.toml", "[project]\nname='x'\n")
        write(self.tmp / "README.md", "uvicorn app.main:create --factory --reload\n")
        write(self.tmp / "app" / "other.py", "api = FastAPI()\n")
        text, _ = self.dockerfile()
        self.assertIn('CMD ["uvicorn", "app.main:create", "--factory", "--host", "0.0.0.0", "--port", "8000"]', text)
        self.assertIn("pip install --no-cache-dir .", text)

    def test_app_dir_is_owned_by_app_user(self):
        # 起動時に /app/logs・/app/data を作るアプリのため、/app 自体も実行ユーザーの持ち物にする
        write(self.tmp / "requirements.txt", "")
        text, _ = self.dockerfile()
        # /data は名前付きボリュームのマウント先。初回のマウントでイメージの所有者が引き継がれる
        self.assertIn("RUN useradd --create-home appuser && mkdir /data && chown appuser:appuser /app /data\n", text)
        self.assertLess(text.index("chown appuser:appuser /app"), text.index("USER appuser"))
        # Django 以外には、DB のシンボリックリンクも migrate も入れない
        self.assertNotIn("db.sqlite3", text)
        self.assertNotIn("migrate", text)

    def test_django_uses_gunicorn(self):
        write(self.tmp / "requirements.txt", "django\n")
        write(self.tmp / "manage.py", "")
        write(self.tmp / "config" / "wsgi.py", "application = get_wsgi_application()\n")
        text, _ = self.dockerfile()
        self.assertIn("pip install --no-cache-dir gunicorn", text)
        # 起動のたびに migrate し、Django の既定の DB（/app/db.sqlite3）の実体をボリューム（/data）に置く
        self.assertIn('CMD ["sh", "-c", "python manage.py migrate --noinput && '
                      'exec gunicorn config.wsgi:application --bind 0.0.0.0:8000"]', text)
        # -f: 手書きの .dockerignore で db.sqlite3 がコピーされていてもビルドを止めない
        self.assertIn("RUN ln -sf /data/db.sqlite3 /app/db.sqlite3\n", text)
        self.assertLess(text.index("ln -sf"), text.index("USER appuser"))

    def test_django_with_uvicorn_still_links_db_and_migrates(self):
        # manage.py があれば、起動コマンドが uvicorn（ASGI）でも Django として DB をボリュームに置く
        write(self.tmp / "requirements.txt", "django\n")
        write(self.tmp / "manage.py", "")
        write(self.tmp / "README.md", "uvicorn config.asgi:application\n")
        text, _ = self.dockerfile()
        self.assertIn('CMD ["sh", "-c", "python manage.py migrate --noinput && '
                      'exec uvicorn config.asgi:application --host 0.0.0.0 --port 8000"]', text)
        self.assertIn("RUN ln -sf /data/db.sqlite3 /app/db.sqlite3\n", text)

    def test_flask_uses_gunicorn(self):
        write(self.tmp / "requirements.txt", "flask\n")
        write(self.tmp / "app.py", "from flask import Flask\nserver = Flask(__name__)\n")
        text, _ = self.dockerfile()
        self.assertIn('CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:8000"]', text)

    def test_tests_are_ignored_for_detection(self):
        write(self.tmp / "requirements.txt", "")
        write(self.tmp / "tests" / "test_app.py", "app = FastAPI()\n")
        text, warnings = self.dockerfile()
        self.assertIn("TODO", text)
        self.assertTrue(any("CMD" in w for w in warnings))

    def test_node_start_script(self):
        write_json(self.tmp / "package.json", {"scripts": {"start": "node index.js"}})
        write(self.tmp / "package-lock.json", "{}")
        text, _ = self.dockerfile("node")
        self.assertIn('CMD ["npm", "start"]', text)
        self.assertIn("RUN mkdir /data && chown node:node /app /data\n", text)
        self.assertIn("npm ci --omit=dev", text)
        self.assertIn("EXPOSE 3000", text)

    def test_existing_dockerfile_is_kept(self):
        write(self.tmp / "Dockerfile", "FROM scratch\nCMD [\"x\"]\n")
        write(self.tmp / ".dockerignore", "x\n")
        text, warnings = self.dockerfile()
        self.assertEqual(text, 'FROM scratch\nCMD ["x"]\n')
        self.assertEqual(len(warnings), 3)
        # /data を作らない Dockerfile では、ボリュームが root の持ち物になり非 root のアプリが書けない
        self.assertTrue(any("/data" in w for w in warnings), warnings)

    def test_existing_dockerfile_with_other_data_paths_warns(self):
        # /app/data・/database は /data ではない
        write(self.tmp / "Dockerfile", "FROM scratch\nRUN mkdir -p /app/data /database\nCMD [\"x\"]\n")
        _, warnings = self.dockerfile()
        self.assertTrue(any("/data" in w for w in warnings), warnings)

    def test_existing_dockerfile_mentioning_data_without_mkdir_warns(self):
        # /data を参照するだけで作らなければ、ボリュームは root の持ち物になる
        write(self.tmp / "Dockerfile", "FROM scratch\n# /data に置く\nENV DB_PATH=/data/app.db\nCMD [\"x\"]\n")
        _, warnings = self.dockerfile()
        self.assertTrue(any("/data" in w for w in warnings), warnings)

    def test_existing_django_dockerfile_warning_mentions_link_and_migrate(self):
        write(self.tmp / "manage.py", "")
        write(self.tmp / "Dockerfile", "FROM scratch\nCMD [\"x\"]\n")
        _, warnings = self.dockerfile()
        data = [w for w in warnings if "/data" in w]
        self.assertEqual(len(data), 1, warnings)
        self.assertIn("ln -sf /data/db.sqlite3 /app/db.sqlite3", data[0])
        self.assertIn("migrate", data[0])

    def test_django_without_command_hints_migrate(self):
        write(self.tmp / "requirements.txt", "django\n")
        write(self.tmp / "manage.py", "")
        text, _ = self.dockerfile()
        # 空のボリュームで起動するため、CMD を書くときに migrate も要ることを示す
        self.assertIn("TODO", text)
        self.assertIn("python manage.py migrate --noinput", text)
        self.assertIn("RUN ln -sf /data/db.sqlite3 /app/db.sqlite3\n", text)

    def test_existing_dockerfile_with_data_dir_has_no_data_warning(self):
        write(self.tmp / "Dockerfile", "FROM scratch\nRUN mkdir /data\nCMD [\"x\"]\n")
        _, warnings = self.dockerfile()
        self.assertFalse(any("/data" in w for w in warnings), warnings)


class DetectPortTest(unittest.TestCase):
    def test_expose(self):
        self.assertEqual(detect_port("FROM x\nEXPOSE 5000/tcp\nEXPOSE 6000\n", "python"), 5000)

    def test_defaults(self):
        self.assertEqual(detect_port("FROM x\n", "python"), 8000)
        self.assertEqual(detect_port("FROM x\n", "node"), 3000)


class DockerignoreTest(TempDirMixin, unittest.TestCase):
    def test_nested_secrets_and_source_named_secrets(self):
        write(self.tmp / "requirements.txt", "")
        write_docker_files(self.tmp, "python")
        lines = (self.tmp / ".dockerignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("**/.env", lines)
        self.assertIn("**/*.key", lines)
        self.assertIn("!**/.env.example", lines)
        self.assertIn("**/secrets.json", lines)
        # secrets.py などのソースは除かない
        self.assertNotIn("secrets.*", lines)
        self.assertNotIn("**/secrets.*", lines)
