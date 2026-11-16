import json
import unittest

from stackgen.config import Config
from stackgen.stack import Service, render_compose, render_nginx, upsert_service, write_stack
from tests.helpers import TempDirMixin

HTTPS = Config("api.portfolio.link", True)
HTTP = Config("api.portfolio.link", False)


class UpsertServiceTest(TempDirMixin, unittest.TestCase):
    def test_sorted_and_deduplicated(self):
        upsert_service(self.tmp, Service("b", 8000))
        upsert_service(self.tmp, Service("a", 3000))
        services = upsert_service(self.tmp, Service("b", 5000))
        self.assertEqual(services, [Service("a", 3000), Service("b", 5000)])
        data = json.loads((self.tmp / "services.json").read_text(encoding="utf-8"))
        self.assertEqual(data, {"services": [{"slug": "a", "port": 3000}, {"slug": "b", "port": 5000}]})


class RenderComposeTest(unittest.TestCase):
    def test_https(self):
        text = render_compose([Service("a", 8000), Service("b", 3000)], HTTPS)
        self.assertIn("image: nginx:1.27-alpine", text)
        self.assertIn('- "443:443"', text)
        self.assertIn("./certs:/etc/nginx/certs:ro", text)
        self.assertIn("build: ./services/a", text)
        self.assertIn('- "3000"', text)
        self.assertIn("path: ./services/b/.env", text)
        self.assertIn("required: false", text)
        # バックエンドのポートはホストに公開しない（nginx の 80/443 だけ）
        self.assertEqual(text.count("ports:"), 1)

    def test_http_has_no_tls(self):
        text = render_compose([Service("a", 8000)], HTTP)
        self.assertNotIn("443", text)
        self.assertNotIn("certs", text)

    def test_no_services(self):
        text = render_compose([], HTTP)
        self.assertIn("nginx:", text)
        self.assertNotIn("depends_on", text)


class RenderNginxTest(unittest.TestCase):
    def test_https(self):
        text = render_nginx([Service("a", 8000)], HTTPS)
        self.assertIn("server_name api.portfolio.link;", text)
        self.assertIn("location /a/ {", text)
        self.assertIn("proxy_pass http://a:8000/;", text)
        self.assertIn("return 301 https://$host$request_uri;", text)
        self.assertIn("ssl_certificate /etc/nginx/certs/fullchain.pem;", text)
        self.assertIn("ssl_certificate_key /etc/nginx/certs/privkey.pem;", text)

    def test_http(self):
        text = render_nginx([Service("a", 8000)], HTTP)
        self.assertNotIn("443", text)
        self.assertNotIn("return 301", text)
        self.assertIn("proxy_pass http://a:8000/;", text)


class WriteStackTest(TempDirMixin, unittest.TestCase):
    def test_writes_files(self):
        write_stack(self.tmp, [Service("a", 8000)], HTTPS)
        self.assertIn("build: ./services/a", (self.tmp / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertIn("location /a/", (self.tmp / "nginx" / "default.conf").read_text(encoding="utf-8"))
        ignore = (self.tmp / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("certs/", ignore)
        self.assertIn("services/*/.env", ignore)
        self.assertNotIn(b"\r\n", (self.tmp / "docker-compose.yml").read_bytes())


class LoadServicesTest(TempDirMixin, unittest.TestCase):
    def test_rejects_invalid(self):
        from stackgen import StackError
        from stackgen.stack import load_services
        from tests.helpers import write_json
        for data in ({"services": [{"slug": "a;b", "port": 1}]}, {"services": [{"slug": "a", "port": "80"}]}, {}):
            with self.subTest(data=data):
                write_json(self.tmp / "services.json", data)
                with self.assertRaises(StackError):
                    load_services(self.tmp)
