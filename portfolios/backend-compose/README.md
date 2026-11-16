# backend-compose

取り込んだポートフォリオ（`portfolios/<スラッグ>/`）のバックエンドを、VPS 用の docker compose のフォルダ `stack/` に登録するコマンド。Claude Code のスキル [/add-portfolio](../../.claude/skills/add-portfolio/SKILL.md) から、[portfolio-importer](../portfolio-importer/README.md) での取り込みの後に呼び出す。Python 3.12 の標準ライブラリだけで動き、検出・コピーは portfolio-importer のモジュールを使う。docker は実行しない（イメージは VPS 上で作る）。

## 設定

[config.json](config.json) に、バックエンドを公開するドメインを書く。`domain` が例（`example.com` など）のままだとコマンドはエラーで止まる。

| 項目 | 内容 |
|---|---|
| `domain` | バックエンドを公開するホスト名（例 `api.your-domain.com`）。VPS の IP を指す DNS レコードを用意しておく |
| `https` | 省略時 `true`。nginx が 443 で待ち受け、80 は 443 へ転送する。証明書は certbot のサービスが取得・更新する（下の「VPS での手順」）。サイトは HTTPS のため、`false`（http）ではフロントエンドから呼べず、フロントエンドはモックのままになる |

`config.json` を変えたら、`python portfolios/backend-compose/add_backend.py --regenerate` で `stack/` を作り直す（下の「使い方」）。

## 使い方

リポジトリのルートで実行する。

```bash
python portfolios/backend-compose/add_backend.py portfolios/<スラッグ> [--enable-api]
```

| 引数 | 内容 |
|---|---|
| `portfolios/<スラッグ>` | portfolio-importer で取り込んだプロジェクト。`nginx`・`certbot`（リバースプロキシ・証明書の更新のサービス名）は使えない |
| `--regenerate` | プロジェクトを指定せずに付け、`config.json` と `stack/services.json` から `stack/` の設定（compose・nginx・`init-cert.sh`・`.gitignore`）だけを作り直す。`config.json` を変えたときに使う。ソースのコピー・`apps.json` の変更は行わない。`apps.json` の `env` に設定と違うスキーム（http / https）のバックエンドの URL があれば `warnings` で知らせる |
| `--enable-api` | フロントエンドを実 API に切り替える（下の表の4）。`/add-portfolio` は登録に成功したら必ず付けて実行し、`apps.json` の `env` でバックエンドの URL を設定する（手順は [SKILL.md](../../.claude/skills/add-portfolio/SKILL.md) の手順5）。付けなければ `apps.json` は変えず、書く内容を `warnings` で案内する |

結果は JSON（`slug`・`service`・`port`・`backendUrl`・`dockerfile`・`frontendEnv`・`warnings`）で標準出力に出る。エラー時は理由を標準エラーに出し、終了コード 1 で終わる（何も書き込まない）。

## 行うこと

| 順 | 内容 | 作成・変更するもの |
|---|---|---|
| 1 | バックエンド（portfolio-importer と同じ検出規則）を、importer と同じ除外規則（`.env`・鍵・DB など）でコピーする。既にあれば、`Dockerfile`・`.dockerignore`・`.env` を残してソースを入れ直す（取り込み元の修正を反映するため） | `stack/services/<スラッグ>/` |
| 2 | Dockerfile がなければ生成する（FastAPI → uvicorn、Django・Flask → gunicorn、node → `npm start`）。DB を置く `/data`（実行ユーザーの持ち物）を作り、Django は `/app/db.sqlite3` を `/data/db.sqlite3` へのシンボリックリンクにして起動のたびに `migrate` する（[DB の永続化](#db-の永続化)）。起動コマンドを判定できなければ TODO を書いて警告する。待ち受けポートは `EXPOSE` から決める（なければ Python 8000・node 3000） | `Dockerfile`・`.dockerignore` |
| 3 | 登録一覧を更新し、compose と nginx の設定を作り直す。ルーティングはパス方式で、`https://<domain>/<スラッグ>/...` を `<スラッグ>` コンテナの `/...` へ転送する。バックエンドのポートはホストに公開しない。各バックエンドに DB 用の名前付きボリューム `<スラッグ>-data` を `/data` にマウントする。`https: true` なら certbot のサービスと初回用の `init-cert.sh` も作る（`false` なら `init-cert.sh` を消す）。`.gitignore` は足りない行だけを追記する | `stack/services.json`・`stack/docker-compose.yml`・`stack/nginx/default.conf`・`stack/init-cert.sh`・`stack/.gitignore` |
| 4 | フロントエンドを配信している（`portfolio-site/apps/apps.json` に登録済み）で `--enable-api` を付けたなら、ソースと `.env.example` から URL 用の環境変数名（`VITE_API_URL` など。名前に URL・BASE・ENDPOINT を含むものを優先）を探し、`env` にバックエンドの URL を書いて `mock` を false（実 API）にする。見つからない・HOST・ORIGIN の名前だけ・http・既に別の値がある場合は変更せず警告する | `portfolio-site/apps/apps.json`（[env の書式](../../portfolio-site/docs/apps.md#appsjson-の書式)） |

- `docker-compose.yml`・`nginx/default.conf` は `services.json` から毎回作り直すため、手で編集しない。
- バックエンドの CORS（サイトのドメインからの呼び出しの許可）は、バックエンド側で設定する。

## VPS での手順

VPS には Docker Compose v2.24 以降が必要（`env_file` の `required: false` を使うため）。`https: true` なら、`domain` の DNS レコードが VPS の IP を指し、80・443 番が外から届くこと（ファイアウォールで開ける）も必要。

1. `stack/` を VPS にアップロードする（例 `scp -r portfolios/backend-compose/stack user@vps:~/portfolio-stack`）。
2. バックエンドが環境変数（API キーなど）を使うなら、`stack/services/<スラッグ>/.env` に書く（`.env.example` を参照）。`letsencrypt/`・`certbot/`・`.env` は git で管理しない。
3. 起動する。
   - `https: true`: `stack/` で `sh init-cert.sh [メールアドレス]` を実行する。証明書（`letsencrypt/live/<domain>/`）がなければ、nginx を止めて certbot の standalone（80 番）で取得し、その後 `docker compose up -d --build` を実行する。証明書があれば起動だけを行うため、2回目以降の起動にも使える。メールアドレスを省略するとメールなしで Let's Encrypt に登録する。取得に失敗したら、止めた nginx を起動し直してエラーで終わる（Let's Encrypt には失敗の回数の制限があるため、原因を直してから再実行する。`DRY_RUN=1 sh init-cert.sh` なら、本番の回数を使わずに取得を試せる。証明書は保存せず、compose の起動もしない。証明書が既にあれば nginx を止めずに webroot で試す）。docker 自体が動かない（デーモンの停止・権限・イメージの取得の失敗）ときは、nginx を止めずにエラーで終わる。
   - `https: false`: `docker compose up -d --build` を実行する。

   nginx と全バックエンドのコンテナが作られる（1つのバックエンドが起動しなくても、nginx とほかのバックエンドは動く）。
4. 動作を確かめてから、`apps.json` の `env` を設定した変更をデプロイする（VPS の起動より先にサイトをデプロイすると、フロントエンドは存在しない API を呼んで動かない）。

### 証明書の更新

手作業は要らない。certbot のコンテナが 12 時間ごとに `certbot renew --webroot` を実行し、期限まで 30 日を切った証明書を更新する（80 番の `/.well-known/acme-challenge/` は nginx が `certbot/` から答える。初回を standalone で取った証明書も webroot で更新される）。nginx は 6 時間ごとに `nginx -s reload` して新しい証明書を読み込む。コンテナに Docker のソケットを渡さないよう、certbot から nginx へは合図しない。

- 更新を試す: `docker compose run --rm --entrypoint certbot certbot renew --webroot -w /var/www/certbot --dry-run`
- すぐに読み込ませる: `docker compose exec nginx nginx -s reload`

### 証明書がないとき

`https: true` で証明書がないまま `docker compose up` すると、nginx は `cannot load certificate "/etc/letsencrypt/live/<domain>/fullchain.pem"` で起動に失敗し、再起動を繰り返す（`docker compose logs nginx` で確かめる）。`sh init-cert.sh` を実行すると取得から起動までを行う。取得に失敗する場合は、DNS と 80 番の開放を確かめる。

### DB の永続化

各バックエンドには名前付きボリューム `<スラッグ>-data`（docker 上の名前は `<プロジェクト名>_<スラッグ>-data`。プロジェクト名は既定で `stack/` のディレクトリ名。`docker volume ls` で確かめる）が `/data` にマウントされ、コンテナを作り直しても（`docker compose up -d --build`・`docker compose down` のあとの `up`）中身が残る。**`docker compose down -v` はボリュームごと全バックエンドの DB を消す**ため使わない。ボリュームは `stack/` の外（Docker の管理領域）にあるため、`stack/` をアップロードし直しても影響しない。

この仕組みより前のイメージで動いていた VPS では、DB はコンテナの中（`/app/db.sqlite3`・`/app/data/app.db`）にあり、新しいイメージで作り直すと引き継がれない（空の DB で起動する）。残したいデータがあれば、更新の前に `docker compose stop <スラッグ>`（止めると WAL の内容が DB に書き戻される）→ `mkdir backup-<スラッグ>` → `docker compose cp <スラッグ>:/app/db.sqlite3 ./backup-<スラッグ>/`（spotify-billboard-playlist は `/app/data/app.db`）で写し、更新のあとに下記の「戻す」手順でボリュームに入れる。

| バックエンド | DB の置き場所 |
|---|---|
| media-feed・task-box-it-develop（Django） | `/data/db.sqlite3`（`/app/db.sqlite3` はそこへのシンボリックリンク。WAL の `-wal`・`-shm` も `/data` に作られる） |
| spotify-billboard-playlist | `/data/app.db`（Dockerfile の `ENV DB_PATH`） |

- 初めて起動したとき（ボリュームが空）は、Django は起動時の `migrate` で、spotify-billboard-playlist は起動時のテーブルの作成で、空の DB から動く。
- 新しく登録したバックエンドも `/data` がマウントされるが、DB をそこに置くかはアプリの設定による。生成する Dockerfile は、Django（`manage.py` がある）なら `/app/db.sqlite3` をリンクする（settings の `BASE_DIR` が `/app` で、DB が既定の `BASE_DIR / 'db.sqlite3'` の前提。違う場合は Dockerfile のリンクを直す）。Django 以外は DB のパスを `/data` 配下に向ける設定（環境変数など）を Dockerfile か `.env` に書く。
- 既にあった Dockerfile は上書きしないため、`/data` を作っていなければ登録時に警告する。そのままだと `/data` が root の持ち物になり、非 root のアプリは書き込めないため、実行ユーザーの持ち物の `/data` を作る行を足す。ボリュームの所有者は空のボリュームを初めてマウントしたときにだけイメージから引き継がれるため、既に起動してボリュームができていれば、Dockerfile を直したあとに初期化（下記）するか、`docker compose run --rm --no-deps --user root --entrypoint chown <スラッグ> -R <実行ユーザー> /data` で所有者を直す。
- バックアップ: `docker compose stop <スラッグ>` → `docker compose cp <スラッグ>:/data/. ./backup-<スラッグ>`（`/data/.` で中身だけを写す。`./backup-<スラッグ>` が既にあっても `data/` の入れ子にならない） → `docker compose start <スラッグ>`（止めてから写すと、書き込み途中の状態を写さない）。戻すときは止めてから `docker compose cp ./backup-<スラッグ>/. <スラッグ>:/data` を実行し、写したファイルの所有者を実行ユーザーに戻してから（`docker compose run --rm --no-deps --user root --entrypoint chown <スラッグ> -R appuser:appuser /data`。node のバックエンドは `node:node`）`docker compose start <スラッグ>` する。
- 初期化（DB を空にする）: `docker compose rm -sf <スラッグ>` → `docker volume rm <プロジェクト名>_<スラッグ>-data` → `docker compose up -d <スラッグ>`。

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
