# backend-compose

取り込んだポートフォリオ（`portfolios/<スラッグ>/`）のバックエンドを、VPS 用の docker compose のフォルダ `stack/` に登録するコマンド。Claude Code のスキル [/add-portfolio](../../.claude/skills/add-portfolio/SKILL.md) から、[portfolio-importer](../portfolio-importer/README.md) での取り込みの後に呼び出す。Python 3.12 の標準ライブラリだけで動き、検出・コピーは portfolio-importer のモジュールを使う。docker は実行しない（イメージは VPS 上で作る）。

## 設定

[config.json](config.json) に、バックエンドを公開するドメインを書く。`domain` が例（`example.com` など）のままだとコマンドはエラーで止まる。

| 項目 | 内容 |
|---|---|
| `domain` | バックエンドを公開するホスト名（例 `api.your-domain.com`）。VPS の IP を指す DNS レコードを用意しておく |
| `https` | 省略時 `true`。nginx が 443 で待ち受け、80 は 443 へ転送する。サイトは HTTPS のため、`false`（http）ではフロントエンドから呼べず、フロントエンドはモックのままになる |

## 使い方

リポジトリのルートで実行する。

```bash
python portfolios/backend-compose/add_backend.py portfolios/<スラッグ>
```

結果は JSON（`slug`・`service`・`port`・`backendUrl`・`dockerfile`・`frontendEnv`・`warnings`）で標準出力に出る。エラー時は理由を標準エラーに出し、終了コード 1 で終わる（何も書き込まない）。

## 行うこと

| 順 | 内容 | 作成・変更するもの |
|---|---|---|
| 1 | バックエンド（portfolio-importer と同じ検出規則）を、importer と同じ除外規則（`.env`・鍵・DB など）でコピーする。既にあればコピーしない | `stack/services/<スラッグ>/` |
| 2 | Dockerfile がなければ生成する（FastAPI → uvicorn、Django・Flask → gunicorn、node → `npm start`）。起動コマンドを判定できなければ TODO を書いて警告する。待ち受けポートは `EXPOSE` から決める（なければ Python 8000・node 3000） | `Dockerfile`・`.dockerignore` |
| 3 | 登録一覧を更新し、compose と nginx の設定を作り直す。ルーティングはパス方式で、`https://<domain>/<スラッグ>/...` を `<スラッグ>` コンテナの `/...` へ転送する。バックエンドのポートはホストに公開しない | `stack/services.json`・`stack/docker-compose.yml`・`stack/nginx/default.conf`・`stack/.gitignore` |
| 4 | フロントエンドを配信している（`portfolio-site/apps/apps.json` に登録済み）なら、ソースと `.env.example` から URL 用の環境変数名（`VITE_API_URL` など）を探し、`env` にバックエンドの URL を書いて `mock` を false（実 API）にする。見つからない・http・既に別の値がある場合は変更せず警告する | `portfolio-site/apps/apps.json`（[env の書式](../../portfolio-site/docs/apps.md#appsjson-の書式)） |

- `docker-compose.yml`・`nginx/default.conf` は `services.json` から毎回作り直すため、手で編集しない。
- バックエンドの CORS（サイトのドメインからの呼び出しの許可）は、バックエンド側で設定する。

## VPS での手順

1. `stack/` を VPS にアップロードする（例 `scp -r portfolios/backend-compose/stack user@vps:~/portfolio-stack`）。
2. `https: true` なら、`stack/certs/` に証明書 `fullchain.pem`・`privkey.pem` を置く（Let's Encrypt の certbot などで取得する）。
3. バックエンドが環境変数（API キーなど）を使うなら、`stack/services/<スラッグ>/.env` に書く（`.env.example` を参照）。`certs/` と `.env` は git で管理しない。
4. `docker compose up -d --build` を実行する。nginx と全バックエンドのコンテナが作られる。

## 開発

```bash
cd portfolios/backend-compose
npm test      # python -m unittest
npm run lint  # 構文チェック（python -m compileall）
```

設計: [docs/specs/add-portfolio-backend-compose/](../../docs/specs/add-portfolio-backend-compose/design.md)
