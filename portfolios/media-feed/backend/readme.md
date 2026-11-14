# backend

Django REST Framework を使った API サーバー。コンテンツ・ユーザー管理、JWT 認証を提供する。

---

## 起動

```bash
cd website/backend
pip install -r requirements.txt
cp .env.example .env    # 初回のみ。APIキー等を記入する
python manage.py migrate
python manage.py runserver
```

API: http://localhost:8000

---

## 環境変数

APIキーなどの設定は `backend/.env` に置く。`config/settings.py` が `python-dotenv` で読み込むため、`runserver` と `tools/` のバッチコマンドの両方から参照できる。

- キーの一覧と用途は [`.env.example`](.env.example) を参照。
- `.env` はgitignore対象。コミットしないこと。
- 既にシェル等で設定されている環境変数は `.env` の値で上書きされない。
- キーを追加したら `.env.example` も更新すること。

---

## ディレクトリ構成

```
backend/
├── api/              モデル・ビュー・シリアライザー・URL定義
├── config/           Django プロジェクト設定
├── tools/            コンテンツ収集・管理バッチコマンド群 → tools/readme.md 参照
├── media/
│   ├── videos/       ダウンロードした動画ファイル
│   └── images/       ダウンロードした画像ファイル
├── manage.py
├── requirements.txt
├── .env              環境変数 (gitignore対象)
├── .env.example      環境変数のテンプレート
└── db.sqlite3
```

---

## データモデル

| モデル | 概要 |
|---|---|
| `User` | カスタムユーザー (username をPK、JWT認証対応) |
| `Content` | 動画・画像コンテンツ (id=SHA256[32]、type: image/video、path/link/title) |
| `Tag` | タグ。Content と多対多 |
| `ContentDetail` | Contentの補足情報 (series_id、series_number) |
| `Series` | シリーズ (series_id をPK、weight で表示頻度を制御) |
| `SeriesQueueItem` | シリーズのランダム表示用キュー |
| `Profile` | ユーザープロフィール (説明 最大800字) |
| `Following` | フォロー関係 (ユーザー間の多対多) |
| `Bookmark` | ブックマーク (ユーザーごとの Content コレクション) |
| `BookmarkedContent` | ブックマーク済みコンテンツ (is_published フラグ付き) |
| `Comment` | コンテンツへのコメント |
| `Article` | 記事 (複数Contentをまとめる、サムネイル自動生成対応) |
| `ArticleTag` | 記事タグ。Article と多対多 |

---

## API エンドポイント

### 認証

| メソッド | パス | 説明 |
|---|---|---|
| POST | `/api/auth/register/` | ユーザー登録 |
| POST | `/api/token/` | JWT アクセストークン取得 |
| POST | `/api/token/refresh/` | JWT トークンリフレッシュ |
| DELETE | `/api/auth/user/` | ユーザー削除 |

### コンテンツ

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/contents/` | コンテンツ一覧 |
| POST | `/api/contents/` | コンテンツ登録 (要認証) |
| GET | `/api/contents/<id>/` | コンテンツ詳細 |
| GET | `/api/contents/<id>/media/` | ローカルメディアファイルの内容を返す (動画/画像ストリーミング) |
| PUT/PATCH | `/api/contents/<id>/` | コンテンツ更新 (要認証) |
| DELETE | `/api/contents/<id>/` | コンテンツ削除 (要認証) |
| GET | `/api/contents/<id>/related/` | 関連コンテンツ (同タグ) |

**`GET /api/contents/` クエリパラメータ:**

| パラメータ | 説明 |
|---|---|
| `type` | `image` / `video` でフィルタ |
| `q` | タイトル・説明のキーワード検索 |
| `tag` | タグ名で絞り込み (複数指定可) |
| `user` | 投稿ユーザー名で絞り込み |
| `exclude_user` | 指定ユーザーを除外 |
| `series_id` | シリーズIDで絞り込み |
| `series_number` | シリーズ内番号で絞り込み |
| `random=true` | ランダム順で返す |

### タグ・ユーザー

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/tags/` | タグ一覧 |
| GET | `/api/users/` | ユーザー一覧 (`?q=` で説明文検索) |

### プロフィール・ソーシャル

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/profile/<username>/` | プロフィール取得 |
| PUT | `/api/profile/<username>/` | プロフィール更新 (要認証・本人のみ) |
| GET | `/api/bookmarks/<username>/` | ブックマーク一覧 |
| POST | `/api/bookmarks/<username>/` | ブックマーク追加 (要認証・本人のみ) |
| DELETE | `/api/bookmarks/<username>/<id>/` | ブックマーク削除 (要認証・本人のみ) |
| GET | `/api/following/<username>/` | フォロー一覧 |
| POST | `/api/following/<username>/` | フォロー追加 (要認証・本人のみ) |
| DELETE | `/api/following/<username>/<target>/` | フォロー解除 (要認証・本人のみ) |
| GET | `/api/comments/<content_id>/` | コメント一覧 |
| POST | `/api/comments/<content_id>/` | コメント投稿 (要認証) |
| PUT | `/api/comments/detail/<id>/` | コメント編集 (要認証・本人のみ) |
| DELETE | `/api/comments/detail/<id>/` | コメント削除 (要認証・本人のみ) |

### 記事

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/articles/` | 記事一覧 (`?q=` 検索、`?tag=` タグ絞り込み) |
| POST | `/api/articles/` | 記事作成 (要認証、サムネイル自動生成) |
| GET | `/api/articles/<id>/` | 記事詳細 |
| DELETE | `/api/articles/<id>/` | 記事削除 (要認証・本人のみ) |
| GET | `/api/article-tags/` | 記事タグ一覧 |

### ブログパーツ

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/blog-parts/` | 記事一覧の埋め込みHTML を生成 |

**`GET /api/blog-parts/` クエリパラメータ:**

| パラメータ | デフォルト | 説明 |
|---|---|---|
| `cols` | `3` | 列数 |
| `rows` | `3` | 行数 |
| `keyword` | (なし) | キーワードフィルタ |
| `color` | `#1a1a2e` | タイトルバーの背景色 |
| `font_color` | `#ffffff` | タイトルバーの文字色 |
| `tile_size` | `150` | タイルの一辺のサイズ (px)。タイルは正方形で統一 |
| `site_url` | `http://localhost:3000` | タイルクリック時のリンク先フロントエンドURL |

---

## バッチコマンド

`tools/` 配下のバッチで各サイトからコンテンツを取得・管理する。  
詳細は [`tools/readme.md`](tools/readme.md) を参照。

```bash
# コンテンツ収集
python manage.py get_hime_channel_videos --number 10
python manage.py get_toxicstream_videos --number 10
python manage.py get_zettai_ero_videos --number 10
python manage.py get_dmm_images -k 素人 -n 20
python manage.py get_dmm_videos -k 人妻 -n 10

# 加工・管理
python manage.py split_video_as_short -n 10
python manage.py make_article_thumbnails
python manage.py calc_series_weight
python manage.py make_series_queue

# ブログパーツ出力
python manage.py make_blog_parts -o output/blog.html --cols 4 --rows 3

# インタラクティブシェル
python manage.py batch_shell
```

---

## 依存ライブラリ

| ライブラリ | 用途 |
|---|---|
| `Django` | Web フレームワーク |
| `djangorestframework` | REST API |
| `djangorestframework-simplejwt` | JWT 認証 |
| `django-cors-headers` | CORS 制御 |
| `Pillow` | 画像処理 |
| `django-filter` | クエリフィルタ |
| `python-dotenv` | `.env` からの環境変数の読み込み |
| `requests` | HTTP リクエスト (スクレイピング・DMM API・ブログパーツ取得) |
| `beautifulsoup4` | HTML パース |
| `pyppeteer` | hime-channel のJavaScript描画ページ処理 |
| `playwright` | DMM 動画URL抽出 |
| `yt-dlp` | zettai-ero の動画ダウンロード |
| `opencv-python` | 動画サムネイル生成 (フレーム抽出) |
| `ffmpeg` / `ffprobe` | 動画分割・再生時間取得 (システムインストール) |
| `docopt` | batch_shell の引数パース (任意) |
