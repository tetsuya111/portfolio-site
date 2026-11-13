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
