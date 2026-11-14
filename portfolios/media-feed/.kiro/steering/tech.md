---
inclusion: always
---

# 技術スタック

- **バックエンド**: Python + Django 5 + Django REST Framework。詳細・APIエンドポイント一覧・コマンドは [backend/readme.md](../../backend/readme.md)。
- **フロントエンド**: Next.js 15（App Router）+ React 19 + TypeScript + MUI v6（ダークテーマ）+ Swiper。詳細は [frontend/readme.md](../../frontend/readme.md)。
- **収集バッチ**: Djangoのmanagementコマンド（`backend/tools/management/commands/`）。詳細は [backend/tools/readme.md](../../backend/tools/readme.md)。
- **認証**: `djangorestframework-simplejwt` によるJWT。ユーザーのPKは `username`（`USER_ID_FIELD` / `USER_ID_CLAIM` も `username`）。アクセストークン1時間、リフレッシュトークン7日。フロントは localStorage に保持する（[frontend/src/lib/auth.ts](../../frontend/src/lib/auth.ts)）。
- **データベース**: SQLite（`backend/db.sqlite3`）。接続設定は `config/settings.py` にハードコードされており、環境変数での切り替えには未対応。
- **メディア配信**: ローカルファイルは `GET /api/contents/<id>/media/` 経由でストリーミングする。S3 上のファイル（`Content.path` が `s3://` で始まる）は `move_content_to_s3` で移行する。バケットは `junk-porn-feed-site`、リージョンは `ap-southeast-2`。
- **外部サービス**: DMM Affiliate API（コンテンツ取得）、Cloudflare Turnstile（bot対策）、Amazon S3（メディア保管）、SMTP / Gmail（問い合わせメール）、OpenAI API（`create_random_articles` の記事文面生成のみ）。
- **スクレイピング基盤**: `requests` + `beautifulsoup4`、JS描画ページは `pyppeteer`（Chrome実行ファイルのパスが必要）と `playwright`（`python -m playwright install chromium`）、動画取得に `yt-dlp`、動画処理に `opencv-python` と システムの `ffmpeg` / `ffprobe`。

## 通信構成

- フロントエンドはAPIをすべて相対パス `/api/...` で呼び、Next.js の `rewrites`（[frontend/next.config.ts](../../frontend/next.config.ts)）がバックエンドへ転送する。転送先は `BACKEND_URL` 環境変数（既定 `http://localhost:8000`）。このため別デバイスから `http://<サーバーIP>:3000` にアクセスしても通信が成立する。
- `trailingSlash: true` のため、APIのパスは末尾スラッシュ必須。rewriteルールも `/api/:path*/` の形で定義されている。新しいエンドポイントを追加する際は末尾スラッシュを揃えること。
- 埋め込み（ブログパーツ）を成立させるため、`X-Frame-Options` を無効化し CSP の `frame-ancestors` で許可元を制御している。許可元を増やす場合は `next.config.ts` を更新する。

## 環境変数

| 変数名 | 対象 | 用途 |
| --- | --- | --- |
| `BACKEND_URL` | フロント | rewriteの転送先バックエンド（既定 `http://localhost:8000`） |
| `NEXT_PUBLIC_API_URL` | フロント | APIのベースURL（既定 `/api`） |
| `NEXT_PUBLIC_TURNSTILE_ENABLED` | フロント | `false` でTurnstile検証を無効化 |
| `DMM_API_ID` / `DMM_AFFILIATE_ID` | バッチ | DMM Affiliate API の認証（`get_dmm_videos` / `get_dmm_images`） |
| `DUGA_AFFILIATE_ID` | バッチ | DUGA のアフィリエイトID（`get_duga`） |
| `OPENAI_API_KEY` | バッチ | `create_random_articles` の文面生成 |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | バック | 問い合わせメールのSMTP設定 |
| `INQUIRY_RECIPIENT_EMAIL` | バック | 問い合わせの通知先（既定は `EMAIL_HOST_USER`） |
| `CLOUDFLARE_TURNSTILE_SECRET_KEY` | バック | Turnstile の検証 |
| `DJANGO_SECRET_KEY` | バック | Djangoの `SECRET_KEY`（未設定なら開発用の既定値） |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | バック | S3アクセス（未設定なら boto3 の既定の解決順に委ねる） |
| `AWS_REGION` | バック | 既定リージョン（既定 `ap-northeast-1`） |
| `MEDIA_S3_BUCKET` | バック | 新規アップロード先・配信元のバケット |
| `MEDIA_BUCKET_REGIONS` | バック | 既定リージョン以外にあるバケットの対応表（`bucket=region,...`） |
| `MEDIA_S3_BUCKET_NEW` | バッチ | `sync_media_region` のコピー先バケット |

バックエンドとバッチの環境変数は `backend/.env` に置く。`settings.py` が `python-dotenv` の `load_dotenv()` で読み込むため、`manage.py` 経由で動くもの（runserver、managementコマンド）はすべてこの値を参照する。キーの一覧とテンプレートは [backend/.env.example](../../backend/.env.example) にあり、これをコピーして `backend/.env` を作る（`backend/.env` はgitignore対象）。環境変数を追加した場合は、この表と `.env.example` の両方を更新すること。

既に設定済みの環境変数は `.env` で上書きされない（シェルやCIで渡した値が優先される）。`backend/tools/set_env.bat` は `.env` 導入前の方法で、秘密情報を含んだままリポジトリに追跡されている。

## 設計上の方針

- 秘密情報（APIキー、シークレット、認証情報）は環境変数で渡し、リポジトリにコミットしない。
- APIのビューは `backend/api/views.py` に集約し、モデルは `backend/api/models.py`、シリアライザは `backend/api/serializers.py`、ルーティングは `backend/api/urls.py` に置く（現状アプリは `api` と `tools` の2つのみ）。
- 収集バッチは1サイト1コマンドとし、`backend/tools/management/commands/` に追加する。DBへの保存は `Content` / `ContentDetail` / `Tag` / `Series` を経由し、`Content.id` の採番（SHA256）はモデルの `save()` に任せる。
- フロントエンドのページ（`src/app/**/page.tsx`）はServer Component のままにし、状態を持つ処理は `src/components/*Client.tsx` に切り出す（既存の全ページがこの形）。
- API呼び出しは `src/lib/api.ts` のクライアント経由に統一する（JWT付与と401時のリフレッシュが入っている）。`fetch` を直接書かない。

## 本番公開前の未対応事項

現状の設定は開発用のまま。公開前に以下を解消すること（未着手）。

- `SECRET_KEY` が既定値のプレースホルダのまま（`DJANGO_SECRET_KEY` を `.env` に設定する）。`DEBUG = True`、`ALLOWED_HOSTS = ['*']`、`CORS_ALLOW_ALL_ORIGINS = True` も本番設定に直す。
- Cloudflare Turnstile のシークレットキーとAWSのアクセスキーは `.env` へ移したが、git履歴と `backend/tools/set_env.bat` には残っている。鍵のローテーションと `set_env.bat` の追跡解除は未対応。
- `backend/db.sqlite3.back` など、リポジトリ内のデータ・生成物の扱いを整理する。

コマンドやAPIの詳細をここに重複して書かず、更新時は必ず [backend/readme.md](../../backend/readme.md) / [frontend/readme.md](../../frontend/readme.md) / [backend/tools/readme.md](../../backend/tools/readme.md) 側を更新すること。
