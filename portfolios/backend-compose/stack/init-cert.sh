#!/bin/sh
# backend-compose が生成したファイル。直接編集しないでください。
# 証明書がなければ certbot の standalone（80 番）で取得し、nginx と全バックエンドを起動する。
# 使い方: sh init-cert.sh [メールアドレス]（省略するとメールなしで Let's Encrypt に登録する）
set -eu
cd "$(dirname "$0")"
DOMAIN=free-junk-porn.site
if [ ! -f "letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
  if [ -n "${1:-}" ]; then ACCOUNT="--email $1"; else ACCOUNT="--register-unsafely-without-email"; fi
  # standalone の certbot が 80 番で答えるため、動いている nginx を止める
  docker compose stop nginx >/dev/null 2>&1 || true
  # shellcheck disable=SC2086
  docker compose run --rm -p 80:80 --entrypoint certbot certbot \
    certonly --standalone -d "$DOMAIN" --agree-tos --non-interactive $ACCOUNT
else
  echo "letsencrypt/live/$DOMAIN/ に証明書があるため、取得は行いません"
fi
docker compose up -d --build
