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
        self.assertIn("./letsencrypt:/etc/letsencrypt:ro", text)
        self.assertNotIn("./certs", text)
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
        self.assertNotIn("certbot", text)
        self.assertNotIn("letsencrypt", text)
        self.assertNotIn("command:", text)

    def test_no_services(self):
        text = render_compose([], HTTP)
        self.assertIn("nginx:", text)
        self.assertNotIn("depends_on", text)


class RenderNginxTest(unittest.TestCase):
    def test_https(self):
        text = render_nginx([Service("a", 8000)], HTTPS)
        self.assertIn("server_name api.portfolio.link;", text)
        self.assertIn("location ~ ^/a(?:/|$) {", text)
        self.assertIn("resolver 127.0.0.11", text)
        self.assertIn("set $upstream_a http://a:8000;", text)
        self.assertIn("rewrite ^/a/?(.*)$ /$1 break;", text)
        self.assertIn("proxy_pass $upstream_a;", text)
        self.assertIn("return 301 https://$host$request_uri;", text)
        self.assertIn("ssl_certificate /etc/nginx/certs/fullchain.pem;", text)
        self.assertIn("ssl_certificate_key /etc/nginx/certs/privkey.pem;", text)

    def test_http(self):
        text = render_nginx([Service("a", 8000)], HTTP)
        self.assertNotIn("443", text)
        self.assertNotIn("return 301", text)
        self.assertIn("proxy_pass $upstream_a;", text)

    def test_hyphenated_slug_variable(self):
        self.assertIn("set $upstream_my_app http://my-app:3000;", render_nginx([Service("my-app", 3000)], HTTP))


class WriteStackTest(TempDirMixin, unittest.TestCase):
    def test_writes_files(self):
        write_stack(self.tmp, [Service("a", 8000)], HTTPS)
        self.assertIn("build: ./services/a", (self.tmp / "docker-compose.yml").read_text(encoding="utf-8"))
        self.assertIn("location ~ ^/a(?:/|$)", (self.tmp / "nginx" / "default.conf").read_text(encoding="utf-8"))
        ignore = (self.tmp / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("certs/", ignore)
        self.assertIn("services/*/.env", ignore)
        self.assertNotIn(b"\r\n", (self.tmp / "docker-compose.yml").read_bytes())


class LoadServicesTest(TempDirMixin, unittest.TestCase):
    def test_rejects_invalid(self):
        from stackgen import StackError
        from stackgen.stack import load_services
        from tests.helpers import write_json
        for data in ({"services": [{"slug": "a;b", "port": 1}]}, {"services": [{"slug": "a\n", "port": 1}]},
{"services": [{"slug": "a", "port": "80"}]}, {"services": [{"slug": "nginx", "port": 80}]},
                     {"services": [{"slug": "docs", "port": 80}]}, {}):
            with self.subTest(data=data):
                write_json(self.tmp / "services.json", data)
                with self.assertRaises(StackError):
                    load_services(self.tmp)


class Round3Test(TempDirMixin, unittest.TestCase):
    def test_compose_has_no_depends_on_and_mounts_certbot(self):
        text = render_compose([Service("a", 8000), Service("b", 3000)], HTTPS)
        self.assertNotIn("depends_on", text)
        self.assertIn("./certbot:/var/www/certbot:ro", text)

    def test_acme_challenge_is_served_over_http(self):
        text = render_nginx([Service("a", 8000)], HTTPS)
        http_server = text.split("listen 443")[0]
        self.assertIn("location /.well-known/acme-challenge/ {\n        root /var/www/certbot;", http_server)
        self.assertIn("return 301", http_server)

    def test_gitignore_has_certbot(self):
        write_stack(self.tmp, [], HTTPS)
        self.assertIn("certbot/", (self.tmp / ".gitignore").read_text(encoding="utf-8"))


class CertbotComposeTest(unittest.TestCase):
    def setUp(self):
        self.text = render_compose([Service("a", 8000)], HTTPS)

    def test_certbot_service_renews_with_webroot(self):
        certbot = self.text.split("  certbot:\n")[1].split("\n  a:\n")[0]
        self.assertIn("image: certbot/certbot:v2.11.0", certbot)
        self.assertIn("restart: unless-stopped", certbot)
        self.assertIn("./letsencrypt:/etc/letsencrypt\n", certbot)
        self.assertIn("./certbot:/var/www/certbot\n", certbot)
        self.assertIn("certbot renew --webroot -w /var/www/certbot --quiet", certbot)
        # compose が $${!} を ${!} に戻す（$ を 1 つだけ書くと compose の変数展開になる）
        self.assertIn("sleep 12h & wait $${!}", certbot)
        self.assertNotIn("docker.sock", self.text)

    def test_nginx_reloads_periodically(self):
        nginx = self.text.split("  certbot:\n")[0]
        self.assertIn("while :; do sleep 21600; nginx -s reload; done & exec nginx -g 'daemon off;'", nginx)
        self.assertIn("./certbot:/var/www/certbot:ro", nginx)

    def test_only_nginx_publishes_ports(self):
        self.assertEqual(self.text.count("ports:"), 1)
