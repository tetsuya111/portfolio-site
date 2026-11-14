import unittest

from importer.envvars import (HTTPS_URL, find_backend_env_names, find_frontend_env_names, frontend_url_env,
                              read_site_url)
from tests.helpers import TempDirMixin, write, write_json


class HttpsUrlTest(unittest.TestCase):
    def test_accepts_https_urls_only(self):
        for ok in ["https://api.example.com", "https://a.example.com:8443/v1/", "https://x-y.example.com/a_b.c~d"]:
            self.assertIsNotNone(HTTPS_URL.fullmatch(ok), ok)
        for ng in ["http://api.example.com", "https://a.example.com/?a=1", "https://a.example.com/#x",
                   'https://a.example.com/"', "https://a b.example.com", "ftp://a.example.com",
                   "https://api.example.com\n"]:
            self.assertIsNone(HTTPS_URL.fullmatch(ng), ng)


class FindFrontendEnvNamesTest(TempDirMixin, unittest.TestCase):
    def test_finds_vite_next_and_env_example_names(self):
        write(self.tmp / "src/api.ts", "const base = import.meta.env.VITE_API_URL ?? '/';\n"
                                       "const key = import.meta.env.VITE_API_KEY;\n")
        write(self.tmp / "lib/client.tsx", "fetch(process.env.NEXT_PUBLIC_BACKEND_URL + '/x')\n")
        write(self.tmp / ".env.example", "PUBLIC_SERVER_ORIGIN=\n# VITE_API_BASE=\nSECRET_API_URL=\n")
        write(self.tmp / "src/App.vue", "import.meta.env.VITE_API_URL\n")
        self.assertEqual(find_frontend_env_names(self.tmp),
                         ["NEXT_PUBLIC_BACKEND_URL", "PUBLIC_SERVER_ORIGIN", "VITE_API_URL"])

    def test_finds_destructured_and_bracket_access(self):
        write(self.tmp / "src/a.ts", "const { VITE_API_URL } = import.meta.env;\n"
                                     "const b = import.meta.env['VITE_BACKEND_URL'];\n")
        self.assertEqual(find_frontend_env_names(self.tmp), ["VITE_API_URL", "VITE_BACKEND_URL"])

    def test_ignores_node_modules_and_other_extensions(self):
        write(self.tmp / "node_modules/x/index.js", "import.meta.env.VITE_API_URL\n")
        write(self.tmp / "README.md", "import.meta.env.VITE_BACKEND_URL\n")
        self.assertEqual(find_frontend_env_names(self.tmp), [])


class FindBackendEnvNamesTest(TempDirMixin, unittest.TestCase):
    def test_finds_frontend_url_like_names(self):
        write(self.tmp / "app/config.py", 'a = os.environ.get("FRONTEND_URL", "x")\n'
                                          "b = os.getenv('SPOTIFY_CLIENT_ID')\n"
                                          'c = os.environ["CORS_ORIGINS"]\n')
        write(self.tmp / "server.js", "app.use(cors({ origin: process.env.CLIENT_URL }))\n"
                                      'const d = process.env["ALLOWED_ORIGIN"]\n')
        write(self.tmp / ".env.example", "FRONTEND_URL=http://127.0.0.1:3000\nDB_PATH=x\n")
        self.assertEqual(find_backend_env_names(self.tmp),
                         ["ALLOWED_ORIGIN", "CLIENT_URL", "CORS_ORIGINS", "FRONTEND_URL"])

    def test_ignores_tests(self):
        write(self.tmp / "tests/test_config.py", 'os.getenv("FRONTEND_URL")\n')
        write(self.tmp / "test_main.py", 'os.getenv("CLIENT_URL")\n')
        write(self.tmp / "src/tests/conftest.py", 'os.environ["TEST_CLIENT_URL"]\n')
        self.assertEqual(find_backend_env_names(self.tmp), [])

    def test_ignores_public_names_and_nested_frontend(self):
        write(self.tmp / "web/.env.example", "API_ORIGIN=\n")
        write(self.tmp / "web/src/a.js", "process.env.WEB_CLIENT_URL\n")
        write(self.tmp / "cfg.py", 'os.getenv("NEXT_PUBLIC_SITE_ORIGIN")\n')
        self.assertEqual(find_backend_env_names(self.tmp, skip_dirs=[self.tmp / "web"]), [])


class ReadSiteUrlTest(TempDirMixin, unittest.TestCase):
    def params(self):
        return self.tmp / "portfolio-site/infra/parameters.json"

    def test_none_without_file(self):
        self.assertIsNone(read_site_url(self.tmp))

    def test_none_with_broken_json_or_bad_domain(self):
        write(self.params(), "{")
        self.assertIsNone(read_site_url(self.tmp))
        for bad in [{"Parameters": {"DomainName": "x/y"}}, {"Parameters": {"DomainName": 1}}, {"Parameters": []},
                    [], {"Parameters": {"DomainName": "localhost"}}, {"Parameters": {"DomainName": '"a.com'}},
                    {"Parameters": {"DomainName": "a.example.com\n"}}]:
            write_json(self.params(), bad)
            self.assertIsNone(read_site_url(self.tmp), bad)

    def test_https_url_from_domain_name(self):
        write_json(self.params(), {"Parameters": {"DomainName": "Portfolio.Example.com"}})
        self.assertEqual(read_site_url(self.tmp), "https://portfolio.example.com")


class FrontendUrlEnvTest(unittest.TestCase):
    def test_origin_names_get_origin_and_others_get_app_url(self):
        env = frontend_url_env(["CORS_ORIGINS", "FRONTEND_URL"], "https://p.example.com/", "my-app", True)
        self.assertEqual(env, {"CORS_ORIGINS": "https://p.example.com",
                               "FRONTEND_URL": "https://p.example.com/apps/my-app/"})

    def test_site_url_path_is_kept_for_app_url(self):
        self.assertEqual(frontend_url_env(["FRONTEND_URL"], "https://p.example.com/pf/", "a", True),
                         {"FRONTEND_URL": "https://p.example.com/pf/apps/a/"})

    def test_unregistered_frontend_gets_origin(self):
        self.assertEqual(frontend_url_env(["FRONTEND_URL"], "https://p.example.com/x", "my-app", False),
                         {"FRONTEND_URL": "https://p.example.com"})

    def test_unsafe_url_gives_empty(self):
        self.assertEqual(frontend_url_env(["FRONTEND_URL"], 'https://p"x.example.com', "a", True), {})
