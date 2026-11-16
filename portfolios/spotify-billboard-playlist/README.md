# Billboard → Spotify Playlist

[ビルボード・データベース](https://billboard.mryogaku.com/) のチャートURLを入力すると、その週の Billboard Hot 100 の曲を収めた **非公開プレイリスト** を自分の Spotify アカウントに作成するローカル Web アプリです。

- 要件・設計: [docs/specs/spotify-billboard-playlist/](../../docs/specs/spotify-billboard-playlist/)
- 構成: `backend/`（Python / FastAPI・スクレイピングバッチ・SQLite）と `frontend/`（Next.js / React）

```
ブラウザ → Next.js (127.0.0.1:3000) ─ /api, /auth を転送 → FastAPI (127.0.0.1:8000)
                                                          ├→ billboard.mryogaku.com（スクレイピング）
                                                          └→ Spotify Accounts / Web API
```

Spotify のトークンとクライアントシークレットはバックエンドだけが保持し、ブラウザには渡しません。

## 必要なもの

- Python 3.12 以上（`python` コマンドで起動できること）
- Node.js 20 以上
- Spotify アカウントと、[Spotify Developer Dashboard](https://developer.spotify.com/dashboard) で作成したアプリ

## 1. Spotify アプリの設定

1. Developer Dashboard でアプリを作成する（API は「Web API」を選択）。
2. **Redirect URIs** に `http://127.0.0.1:3000/auth/callback` を登録する（Spotify は `localhost` を受け付けないため `127.0.0.1` を使う）。
3. 開発モードのアプリは、Dashboard の **User Management** に登録したユーザーしか使えない。自分のアカウントを登録しておく。
4. Client ID と Client Secret を控える。

## 2. セットアップ

```bash
cd portfolios/spotify-billboard-playlist
npm run setup                       # backend/.venv 作成・Python 依存と frontend の npm 依存をインストール
cp backend/.env.example backend/.env  # SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET を記入
```

## 3. 起動

ターミナルを2つ開く。

```bash
# バックエンド（backend/ で実行）
.venv/Scripts/python -m uvicorn app.main:create_default_app --factory --env-file .env --host 127.0.0.1 --port 8000
# macOS / Linux は .venv/bin/python

# フロントエンド（frontend/ で実行）
npm run dev
```

ブラウザで **http://127.0.0.1:3000** を開く（`localhost` で開くと Cookie が別扱いになりログインできない）。

1. 「Spotifyでログイン」を押して許可する。
2. チャートURLを入力する（例）。
   - `https://billboard.mryogaku.com/`（最新週）
   - `https://billboard.mryogaku.com/php/chart.php?date=2025-11-15`（指定した週）
3. 「プレイリストを作成」を押す。完了すると Spotify へのリンクと、見つからなかった曲の一覧が表示される。

## バッチ（スクレイピングのみ）

DB（既定 `backend/data/app.db`）に登録された未処理のURLをまとめて取得する。

```bash
cd backend
.venv/Scripts/python -m app.batch --add "https://billboard.mryogaku.com/php/chart.php?date=2025-11-15"
```

受け付けるURLは `billboard.mryogaku.com` のページのみ。

- トップページは、最新週の Hot 100 全順位ページをたどって取得する。
- `chart.php?date=YYYY-MM-DD`・`dispHot100.php?date=YYYY-MM-DD`（スマホ版 `/s/…` を含む）は、同じ日付の Hot 100 全順位ページ（100曲）に置き換えて取得する。
- それ以外のページはそのまま取得し、Hot 100 全順位ページと同じ表の形で曲が並んでいれば使う。曲が見つからなければエラーになる。100曲を超える場合は、先頭の100曲だけがプレイリストの対象になる。
  - `alltime.php?page=N` など、曲を `<script>` に埋め込んで表示する詳細表示ページは、そのページに載っている曲だけを直接取り出す（2026-11 時点では1ページ20曲）。複数ページはまとめず、ページごとに登録する。

## テスト・lint・ビルド

```bash
cd portfolios/spotify-billboard-playlist
npm test        # pytest（backend）+ vitest（frontend）
npm run lint    # ruff（backend）+ eslint・tsc（frontend）
npm run build   # next build
```

## 補足

- HTTPS の検証には OS の証明書ストアを使う（ウイルス対策ソフトの HTTPS 検査などで独自のルート証明書が入っている環境でも、検証を無効にせず接続できるようにするため）。
- ログイン状態はバックエンドのメモリに保持するため、バックエンドを再起動すると再ログインが必要。
- Next.js の匿名テレメトリを止めたい場合は環境変数 `NEXT_TELEMETRY_DISABLED=1` を設定する。
- Windows でドライブ文字が小文字のパス（`c:\…`）から vitest を起動すると失敗するため、`npm test` は `frontend/scripts/vitest.mjs` 経由でパスを正規化して起動している。

## セキュリティ上の制限と設定

- チャートの取得（`POST /api/charts`）はログイン必須。利用者ごとに 60 秒あたり 10 回まで（超えると 429）。
- 保存するチャートURLは最新 1000 件まで（処理済みのものを古い順に曲データごと削除。未処理のものは消さない）。
- ログインセッションは作成から 7 日、または 24 時間操作が無いと切れる。同時に保持するのは全体で 1000 件・1 アカウントあたり 5 件まで（超えると最後に使われたのが最も古いものを削除）。
- 状態を変える POST は、フロントエンドのオリジンからのみ受け付ける（`Origin` が無い場合は `Sec-Fetch-Site: same-origin` のときだけ）。ログイン中は `GET /api/me` が返す `csrf_token` を `X-CSRF-Token` ヘッダーで送る必要がある。
- `FRONTEND_URL`・`SPOTIFY_REDIRECT_URI` は https で指定する。http はループバックのホスト（`127.0.0.1`・`localhost`・`::1`）だけ許され、それ以外はバックエンドが起動しない。
- Cookie の Secure 属性は `COOKIE_SECURE=true|false` で指定する。未指定なら `FRONTEND_URL` が https のときだけ付ける。`false` は `FRONTEND_URL` がループバックのときだけ指定できる。

## ポートフォリオサイトで公開する

ポートフォリオサイト（[portfolio-site/](../../portfolio-site/)）の `/apps/spotify-billboard-playlist/` で、VPS のバックエンドにつないで動かす手順。サイトの CloudFront が `/apps/spotify-billboard-playlist/api/*`・`/auth/*` を VPS に転送するため、ブラウザからはフロントエンドと API が同じオリジン・同じパスの下に見える（Cookie は `SameSite=Lax` のまま、CORS は使わない）。

```
ブラウザ → CloudFront（サイトのドメイン）
            ├ /apps/spotify-billboard-playlist/        → S3（静的出力したフロントエンド）
            └ /apps/spotify-billboard-playlist/api/*, /auth/*
                → （先頭の /apps を取り除く）https://<VPS>/spotify-billboard-playlist/... → nginx → FastAPI（/api/..., /auth/...）
```

以下、サイトが `https://portfolio.example.com`、VPS が `vps.example.com` の場合の例。

1. **VPS の `.env`**（[backend-compose](../backend-compose/README.md) の `stack/services/spotify-billboard-playlist/.env`）:

   ```
   SPOTIFY_CLIENT_ID=<Dashboard の Client ID>
   SPOTIFY_CLIENT_SECRET=<Dashboard の Client Secret>
   FRONTEND_URL=https://portfolio.example.com/apps/spotify-billboard-playlist
   SPOTIFY_REDIRECT_URI=https://portfolio.example.com/apps/spotify-billboard-playlist/auth/callback
   ```

   - `FRONTEND_URL` はサイトのドメインにフロントエンドのパスを付けた URL（末尾の `/` なし）。`Origin` の確認はこのオリジン（`https://portfolio.example.com`）で行い、Cookie はこのパスの下（state は `/apps/spotify-billboard-playlist/auth`、セッションは `/apps/spotify-billboard-playlist/`）に発行する。ログイン後はこの URL + `/` に戻る。
   - `SPOTIFY_REDIRECT_URI` は `FRONTEND_URL` + `/auth/callback`。VPS のドメインではなくサイトのドメインにする（state の Cookie が届かないため、`FRONTEND_URL` と違うスキーム・ホストや `<パス>/auth/` の外にするとバックエンドが起動しない）。
   - `COOKIE_SECURE` は指定しない（https なので Secure が付く）。
   - 変えたら `docker compose up -d spotify-billboard-playlist` で作り直す。
2. **Spotify Developer Dashboard**: アプリの **Redirect URIs** に手順1の `SPOTIFY_REDIRECT_URI` を追加する。開発モードのアプリは **User Management** に登録したユーザーしかログインできないため、試してもらうアカウントを登録する（登録していないアカウントは Spotify の画面でエラーになる）。
3. **CloudFront**: サイトのスタックのパラメーター `BackendDomainName` に VPS のドメイン（`vps.example.com`）を入れて `aws cloudformation deploy` する（[portfolio-site/infra/README.md](../../portfolio-site/infra/README.md#パラメーター)）。dev のスタックも同じ VPS を指してよいが、`FRONTEND_URL` は1つしか指定できないため、ログインできるのは `.env` に書いたサイトだけ。
4. **フロントエンド**: [portfolio-site/apps/apps.json](../../portfolio-site/apps/apps.json) の `"mock": false` のまま、サイトをデプロイする（`next build` が API・認証のパスに `/apps/spotify-billboard-playlist` を付ける）。**手順3のスタックの更新を先に行う**（`BackendDomainName` が空のままだと API が S3 に届いて 404 になり、画面にエラーが出る。VPS を用意できない間は `"mock": true` に戻す）。
5. **動作確認**: サイトの `/apps/spotify-billboard-playlist/` を開き、ログイン → Spotify で許可 → 同じページに「ログイン中」で戻る → チャートの URL を入れてプレイリストを作成 →「Spotifyで開く」→ 再読み込みしてもログイン中 → ログアウトで「未ログイン」に戻る、を確かめる。

制限:

- セッションはバックエンドのメモリーに持つため、コンテナの再起動・作り直しでログインが切れる。
- CloudFront のエラーページの設定はサイト全体に効くため、存在しない API（404）は JSON ではなくサイトの 404 ページになる（画面には「エラーが発生しました（HTTP 404）」と出る）。それ以外のエラー（400・401・403・429・5xx など）はバックエンドの応答のまま届く。エラー（404 を含む）は CloudFront にキャッシュされない。
- VPS へ直接（`https://vps.example.com/spotify-billboard-playlist/...`）来た状態を変えるリクエストは、`Origin` がサイトと違うため 403 になる。
