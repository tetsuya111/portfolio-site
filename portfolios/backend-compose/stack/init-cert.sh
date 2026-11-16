#!/bin/sh
# backend-compose が生成したファイル。直接編集しないでください。
# 証明書がなければ certbot の standalone（80 番）で取得し、nginx と全バックエンドを起動する。
# 使い方: sh init-cert.sh [メールアドレス]（省略するとメールなしで Let's Encrypt に登録する）
set -eu
cd "$(dirname "$0")"
DOMAIN=free-junk-porn.site
# certbot は live/ を root だけが読める権限で作るため、ホストのユーザーではなくコンテナ（root）で確かめる
if ! docker compose run --rm --no-deps --entrypoint test certbot -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem"; then
  # メールアドレスは 1 つの引数として渡す
  if [ -n "${1:-}" ]; then set -- --email "$1"; else set -- --register-unsafely-without-email; fi
  # standalone の certbot が 80 番で答えるため、動いている nginx を止める
  docker compose stop nginx >/dev/null 2>&1 || true
  if ! docker compose run --rm -p 80:80 --entrypoint certbot certbot \
      certonly --standalone -d "$DOMAIN" --agree-tos --non-interactive "$@"; then
    echo "証明書を取得できませんでした。DNS が VPS を指しているか、80 番が外から届くかを確かめてください" >&2
    # 止めた nginx を動いていた状態に戻す（証明書がなければ起動に失敗する）
    docker compose start nginx >/dev/null 2>&1 || true
    exit 1
  fi
else
  echo "letsencrypt/live/$DOMAIN/ に証明書があるため、取得は行いません"
fi
docker compose up -d --build
