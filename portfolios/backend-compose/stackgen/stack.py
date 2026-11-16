"""登録したバックエンドの一覧（services.json）から、docker-compose.yml と nginx の設定を作り直す。

compose・nginx の設定は追記ではなく、正本の services.json から毎回作り直す（重複・消し忘れを防ぐ）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from importer import PortfolioError
from importer.copier import validate_slug
from stackgen import StackError
from stackgen.config import Config

NGINX_IMAGE = "nginx:1.27-alpine"
CERTBOT_IMAGE = "certbot/certbot:v2.11.0"
# 6 時間ごとに reload する
NGINX_COMMAND = ('["/bin/sh", "-c", '
                 '"while :; do sleep 21600; nginx -s reload; done & exec nginx -g \'daemon off;\'"]')
# 12 時間ごとに renew する。compose は $$ を $ に戻す。sleep & wait にして停止の TERM ですぐ終わる
CERTBOT_ENTRYPOINT = ('["/bin/sh", "-c", "trap exit TERM; while :; do '
                      'certbot renew --webroot -w /var/www/certbot --quiet; sleep 12h & wait $${!}; done"]')
# バックエンドのサービス名（スラッグ）に使えない、compose のサービス名
RESERVED_SERVICES = {"nginx"}

GITIGNORE = """\
# TLS 証明書（VPS 上で配置する。fullchain.pem・privkey.pem）
certs/
# certbot の HTTP-01 チャレンジのファイル（VPS 上で作られる）
certbot/
# バックエンドの秘密情報（VPS 上で配置する）
services/*/.env
"""


@dataclass(frozen=True)
class Service:
    slug: str
    port: int


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def load_services(stack_dir: Path) -> list[Service]:
    path = stack_dir / "services.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data["services"]
        services = [Service(i["slug"], i["port"]) for i in items]
    except (ValueError, KeyError, TypeError) as e:
        raise StackError(f'services.json の形式が不正です（{{"services": [{{"slug", "port"}}]}} が必要です）: {e}') from e
    for s in services:
        # 値は compose・nginx の設定にそのまま書くため、取り込みと同じ規則で使える文字を限定する
        try:
            if not isinstance(s.slug, str) or s.slug in RESERVED_SERVICES:
                raise PortfolioError("")
            validate_slug(s.slug)
        except PortfolioError as e:
            raise StackError(f"services.json の slug「{s.slug}」が不正です") from e
        if not isinstance(s.port, int) or isinstance(s.port, bool) or not 1 <= s.port <= 65535:
            raise StackError(f"services.json の {s.slug} の port が不正です")
    return services


def upsert_service(stack_dir: Path, svc: Service) -> list[Service]:
    """svc を登録（同じスラッグは置き換え）して services.json に保存し、スラッグ順の一覧を返す。"""
    services = {s.slug: s for s in load_services(stack_dir)}
    services[svc.slug] = svc
    result = [services[k] for k in sorted(services)]
    data = {"services": [{"slug": s.slug, "port": s.port} for s in result]}
    _write(stack_dir / "services.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return result


def render_compose(services: list[Service], cfg: Config) -> str:
    lines = [
        "# backend-compose が services.json から生成したファイル。直接編集せず、add_backend.py で登録してください。",
        "services:",
        "  nginx:",
        f"    image: {NGINX_IMAGE}",
        "    restart: unless-stopped",
        "    ports:",
        '      - "80:80"',
    ]
    if cfg.https:
        lines.append('      - "443:443"')
    lines += ["    volumes:", "      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro"]
    if cfg.https:
        # certbot と共有する証明書（live/ はシンボリックリンクのためディレクトリごと共有する）と、
        # certbot（--webroot）の HTTP-01 チャレンジのファイル置き場
        lines += ["      - ./letsencrypt:/etc/letsencrypt:ro", "      - ./certbot:/var/www/certbot:ro",
                  # 更新された証明書を読み込むため、裏で定期的に reload する（certbot から合図するには
                  # Docker のソケットが要り権限が広がるため使わない）。exec で nginx を PID 1 にし停止の合図を受ける
                  f"    command: {NGINX_COMMAND}",
                  "  certbot:",
                  f"    image: {CERTBOT_IMAGE}",
                  "    restart: unless-stopped",
                  "    volumes:",
                  "      - ./letsencrypt:/etc/letsencrypt",
                  "      - ./certbot:/var/www/certbot",
                  # 期限まで 30 日を切った証明書だけを更新する。初回を standalone で取った証明書も webroot で更新する
                  f"    entrypoint: {CERTBOT_ENTRYPOINT}"]
    # depends_on は書かない（1つのバックエンドの起動失敗で nginx・ほかのバックエンドまで止めないため。
    # 転送先は要求のたびに名前を引くので、起動順に依存しない）
    for s in services:
        lines += [
            f"  {s.slug}:",
            f"    build: ./services/{s.slug}",
            "    restart: unless-stopped",
            # バックエンドのポートはホストに公開せず、nginx からだけ届くようにする
            "    expose:",
            f'      - "{s.port}"',
            "    env_file:",
            f"      - path: ./services/{s.slug}/.env",
            "        required: false",
        ]
    return "\n".join(lines) + "\n"


_PROXY_HEADERS = """\
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /{slug};
"""


def _locations(services: list[Service]) -> str:
    # 転送先を変数にし、Docker の DNS（127.0.0.11）で要求のたびに名前を引く。固定のホスト名だと、
    # コンテナを作り直して IP が変わると 502 になり、起動していないバックエンドがあると nginx 自体が起動しない
    blocks = ["    resolver 127.0.0.11 valid=10s ipv6=off;\n"]
    for s in services:
        var = f"$upstream_{s.slug.replace('-', '_')}"
        # 前置き /<スラッグ> を外して転送する（/<スラッグ>/api/x?q=1 → /api/x?q=1、/<スラッグ> → /）。
        # スラッグは英小文字・数字・ハイフンだけのため、正規表現にそのまま書いてよい
        blocks.append(f"    location ~ ^/{s.slug}(?:/|$) {{\n"
                      f"        set {var} http://{s.slug}:{s.port};\n"
                      f"        rewrite ^/{s.slug}/?(.*)$ /$1 break;\n"
                      f"        proxy_pass {var};\n"
                      + _PROXY_HEADERS.format(slug=s.slug)
                      + "    }\n")
    blocks.append("    location / {\n        return 404;\n    }\n")
    return "\n".join(blocks)


def render_nginx(services: list[Service], cfg: Config) -> str:
    head = "# backend-compose が services.json から生成したファイル。直接編集せず、add_backend.py で登録してください。\n"
    if not cfg.https:
        return (head + "server {\n    listen 80;\n"
                f"    server_name {cfg.domain};\n\n" + _locations(services) + "}\n")
    return (
        head
        + "server {\n    listen 80;\n"
        f"    server_name {cfg.domain};\n"
        # 証明書の更新（certbot certonly --webroot -w ./certbot）のため、チャレンジだけは http で答える
        "    location /.well-known/acme-challenge/ {\n        root /var/www/certbot;\n    }\n"
        "    location / {\n        return 301 https://$host$request_uri;\n    }\n}\n\n"
        "server {\n    listen 443 ssl;\n"
        f"    server_name {cfg.domain};\n"
        "    ssl_certificate /etc/nginx/certs/fullchain.pem;\n"
        "    ssl_certificate_key /etc/nginx/certs/privkey.pem;\n\n"
        + _locations(services) + "}\n"
    )


def write_stack(stack_dir: Path, services: list[Service], cfg: Config) -> None:
    _write(stack_dir / "docker-compose.yml", render_compose(services, cfg))
    _write(stack_dir / "nginx" / "default.conf", render_nginx(services, cfg))
    if not (stack_dir / ".gitignore").exists():
        _write(stack_dir / ".gitignore", GITIGNORE)
