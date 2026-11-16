#!/bin/sh
# backend-compose が生成したファイル。直接編集しないでください。
# 証明書がなければ certbot の standalone（80 番）で取得し、nginx と全バックエンドを起動する。
# 使い方: sh init-cert.sh [メールアドレス]（省略するとメールなしで Let's Encrypt に登録する）
#         DRY_RUN=1 sh init-cert.sh … 本番の発行回数を使わずに取得を試す（証明書は保存せず、起動もしない）
set -eu
cd "$(dirname "$0")"
DOMAIN=free-junk-porn.site
# certbot は live/ を root だけが読める権限で作るため、ホストのユーザーではなくコンテナ（root）で確かめる。
# docker 自体の失敗（デーモン停止・権限・イメージの取得）は set -e でここで止め、「証明書なし」と取り違えない
HAVE_CERT=$(docker compose run --rm --no-deps -T --entrypoint sh certbot -c "if [ -f /etc/letsencrypt/live/$DOMAIN/fullchain.pem ]; then echo yes; else echo no; fi")
case "$HAVE_CERT" in yes|no) ;; *)
  echo "証明書の有無を確かめられませんでした（出力: $HAVE_CERT）" >&2
  exit 1 ;;
esac
# メールアドレスは 1 つの引数として渡す。--cert-name で、別名の系列（<domain>-0001）を作らず nginx が読むパスに取得する
if [ -n "${1:-}" ]; then set -- --email "$1"; else set -- --register-unsafely-without-email; fi
set -- "$@" -d "$DOMAIN" --cert-name "$DOMAIN" --agree-tos --non-interactive
if [ "${DRY_RUN:-}" = 1 ]; then set -- "$@" --dry-run; fi
if [ "$HAVE_CERT" = yes ]; then
  if [ "${DRY_RUN:-}" = 1 ]; then
    # 証明書がある（nginx が動ける）ので、nginx を止めずに webroot で試す
    docker compose run --rm --no-deps --entrypoint certbot certbot \
      certonly --webroot -w /var/www/certbot "$@"
    echo "取得を試せました（DRY_RUN のため証明書は保存していません）"
    exit 0
  fi
  echo "letsencrypt/live/$DOMAIN/ に証明書があるため、取得は行いません"
else
  # standalone の certbot が 80 番で答えるため、動いている nginx を止める
  docker compose stop nginx >/dev/null 2>&1 || true
  if ! docker compose run --rm -p 80:80 --entrypoint certbot certbot certonly --standalone "$@"; then
    echo "証明書を取得できませんでした。DNS が VPS を指しているか、80 番が外から届くかを確かめてください" >&2
    # 止めた nginx を動いていた状態に戻す（証明書がまだなければ、nginx も起動に失敗する）
    docker compose start nginx || echo "nginx を起動できませんでした（docker compose logs nginx を確かめてください）" >&2
    exit 1
  fi
  if [ "${DRY_RUN:-}" = 1 ]; then
    echo "取得を試せました（DRY_RUN のため証明書は保存していません）"
    docker compose start nginx || true
    exit 0
  fi
fi
docker compose up -d --build
