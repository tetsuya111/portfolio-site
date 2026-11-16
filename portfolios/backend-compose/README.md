# backend-compose

取り込んだポートフォリオ（`portfolios/<スラッグ>/`）のバックエンドを、VPS 用の docker compose のフォルダ `stack/` に登録するコマンド。Claude Code のスキル [/add-portfolio](../../.claude/skills/add-portfolio/SKILL.md) から、[portfolio-importer](../portfolio-importer/README.md) での取り込みの後に呼び出す。Python 3.12 の標準ライブラリだけで動き、検出・コピーは portfolio-importer のモジュールを使う。docker は実行しない（イメージは VPS 上で作る）。

## 設定

[config.json](config.json) に、バックエンドを公開するドメインを書く。`domain` が例（`example.com` など）のままだとコマンドはエラーで止まる。

| 項目 | 内容 |
|---|---|
| `domain` | バックエンドを公開するホスト名（例 `api.your-domain.com`）。VPS の IP を指す DNS レコードを用意しておく |
| `https` | 省略時 `true`。nginx が 443 で待ち受け、80 は 443 へ転送する。証明書は certbot のサービスが取得・更新する（下の「VPS での手順」）。サイトは HTTPS のため、`false`（http）ではフロントエンドから呼べず、フロントエンドはモックのままになる |

`config.json` を変えたら、次で `stack/` を作り直す（ソースのコピーは行わない）。

```bash
cd portfolios/backend-compose
python -c "import sys; sys.path[:0]=['.','../portfolio-importer']; from pathlib import Path; from stackgen.config import load_config; from stackgen.stack import load_services, write_stack; s=Path('stack'); write_stack(s, load_services(s), load_config(Path('config.json')))"
```

## 使い方

リポジトリのルートで実行する。

```bash
python portfolios/backend-compose/add_backend.py portfolios/<スラッグ> [--enable-api]
```

| 引数 | 内容 |
|---|---|
| `portfolios/<スラッグ>` | portfolio-importer で取り込んだプロジェクト。`nginx`（リバースプロキシのサービス名）は使えない |
| `--enable-api` | フロントエンドを実 API に切り替える（下の表の4）。`/add-portfolio` は登録に成功したら必ず付けて実行し、`apps.json` の `env` でバックエンドの URL を設定する（手順は [SKILL.md](../../.claude/skills/add-portfolio/SKILL.md) の手順5）。付けなければ `apps.json` は変えず、書く内容を `warnings` で案内する |

結果は JSON（`slug`・`service`・`port`・`backendUrl`・`dockerfile`・`frontendEnv`・`warnings`）で標準出力に出る。エラー時は理由を標準エラーに出し、終了コード 1 で終わる（何も書き込まない）。

## 行うこと

| 順 | 内容 | 作成・変更するもの |
|---|---|---|
| 1 | バックエンド（portfolio-importer と同じ検出規則）を、importer と同じ除外規則（`.env`・鍵・DB など）でコピーする。既にあれば、`Dockerfile`・`.dockerignore`・`.env` を残してソースを入れ直す（取り込み元の修正を反映するため） | `stack/services/<スラッグ>/` |
| 2 | Dockerfile がなければ生成する（FastAPI → uvicorn、Django・Flask → gunicorn、node → `npm start`）。起動コマンドを判定できなければ TODO を書いて警告する。待ち受けポートは `EXPOSE` から決める（なければ Python 8000・node 3000） | `Dockerfile`・`.dockerignore` |
| 3 | 登録一覧を更新し、compose と nginx の設定を作り直す。ルーティングはパス方式で、`https://<domain>/<スラッグ>/...` を `<スラッグ>` コンテナの `/...` へ転送する。バックエンドのポートはホストに公開しない。`https: true` なら certbot のサービスと初回用の `init-cert.sh` も作る（`false` なら `init-cert.sh` を消す）。`.gitignore` は足りない行だけを追記する | `stack/services.json`・`stack/docker-compose.yml`・`stack/nginx/default.conf`・`stack/init-cert.sh`・`stack/.gitignore` |
| 4 | フロントエンドを配信している（`portfolio-site/apps/apps.json` に登録済み）で `--enable-api` を付けたなら、ソースと `.env.example` から URL 用の環境変数名（`VITE_API_URL` など。名前に URL・BASE・ENDPOINT を含むものを優先）を探し、`env` にバックエンドの URL を書いて `mock` を false（実 API）にする。見つからない・HOST・ORIGIN の名前だけ・http・既に別の値がある場合は変更せず警告する | `portfolio-site/apps/apps.json`（[env の書式](../../portfolio-site/docs/apps.md#appsjson-の書式)） |

- `docker-compose.yml`・`nginx/default.conf` は `services.json` から毎回作り直すため、手で編集しない。
- バックエンドの CORS（サイトのドメインからの呼び出しの許可）は、バックエンド側で設定する。

## VPS での手順

VPS には Docker Compose v2.24 以降が必要（`env_file` の `required: false` を使うため）。`https: true` なら、`domain` の DNS レコードが VPS の IP を指し、80・443 番が外から届くこと（ファイアウォールで開ける）も必要。

1. `stack/` を VPS にアップロードする（例 `scp -r portfolios/backend-compose/stack user@vps:~/portfolio-stack`）。
2. バックエンドが環境変数（API キーなど）を使うなら、`stack/services/<スラッグ>/.env` に書く（`.env.example` を参照）。`letsencrypt/`・`certbot/`・`.env` は git で管理しない。
3. 起動する。
   - `https: true`: `stack/` で `sh init-cert.sh [メールアドレス]` を実行する。証明書（`letsencrypt/live/<domain>/`）がなければ、nginx を止めて certbot の standalone（80 番）で取得し、その後 `docker compose up -d --build` を実行する。証明書があれば起動だけを行うため、2回目以降の起動にも使える。メールアドレスを省略するとメールなしで Let's Encrypt に登録する。試すときに Let's Encrypt の発行回数の制限が気になる場合は、スクリプトの `certonly` に `--staging` を足して試す（その証明書はブラウザに信頼されないため、試した後に `letsencrypt/` を消して取り直す）。
   - `https: false`: `docker compose up -d --build` を実行する。

   nginx と全バックエンドのコンテナが作られる（1つのバックエンドが起動しなくても、nginx とほかのバックエンドは動く）。
4. 動作を確かめてから、`apps.json` の `env` を設定した変更をデプロイする（VPS の起動より先にサイトをデプロイすると、フロントエンドは存在しない API を呼んで動かない）。

### 証明書の更新

手作業は要らない。certbot のコンテナが 12 時間ごとに `certbot renew --webroot` を実行し、期限まで 30 日を切った証明書を更新する（80 番の `/.well-known/acme-challenge/` は nginx が `certbot/` から答える。初回を standalone で取った証明書も webroot で更新される）。nginx は 6 時間ごとに `nginx -s reload` して新しい証明書を読み込む。コンテナに Docker のソケットを渡さないよう、certbot から nginx へは合図しない。

- 更新を試す: `docker compose run --rm --entrypoint certbot certbot renew --webroot -w /var/www/certbot --dry-run`
- すぐに読み込ませる: `docker compose exec nginx nginx -s reload`

### 証明書がないとき

`https: true` で証明書がないまま `docker compose up` すると、nginx は `cannot load certificate "/etc/letsencrypt/live/<domain>/fullchain.pem"` で起動に失敗し、再起動を繰り返す（`docker compose logs nginx` で確かめる）。`sh init-cert.sh` を実行すると取得から起動までを行う。取得に失敗する場合は、DNS と 80 番の開放を確かめる。

## HTTPS で公開できたあとに戻すもの

PR #58 で、http の VPS で試すために次を一時的に変えている。HTTPS で公開できたら元に戻す（戻す作業はこの README の範囲外。目印は `TODO（テスト用に一時的に無効化）`）。

| ファイル | 戻す内容 |
|---|---|
| [stackgen/frontend_env.py](stackgen/frontend_env.py) | `update_apps_json` の、URL が https でなければモックのままにする確認のコメントアウトを外す |
| [tests/test_frontend_env.py](tests/test_frontend_env.py) | 上の確認のテストの skip を外す |
| [portfolio-site/src/lib/apps-manifest.ts](../../portfolio-site/src/lib/apps-manifest.ts) | `env` の値を `https://` に限る検証を戻す |
| [portfolio-site/tests/apps-manifest.test.ts](../../portfolio-site/tests/apps-manifest.test.ts) | 上の検証のテストを有効にする |
| [portfolio-site/apps/apps.json](../../portfolio-site/apps/apps.json) | media-feed・task-box-it-develop の `env` の URL を `http://` から `https://` にする |

## 開発

```bash
cd portfolios/backend-compose
npm test      # python -m unittest
npm run lint  # 構文チェック（python -m compileall）
```

設計: [docs/specs/add-portfolio-backend-compose/](../../docs/specs/add-portfolio-backend-compose/design.md)
