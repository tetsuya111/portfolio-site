# tools

`website/backend/manage.py` から起動できるバッチコマンド集。  
各サイトのコンテンツ情報を取得し、websiteのデータベースに保存する。

---

## コマンド一覧

### コンテンツ取得系

| コマンド | 対象 | ダウンロード方式 |
|---|---|---|
| `get_hime_channel_videos` | hime-channel.com | pyppeteer → MP4直接DL |
| `get_toxicstream_videos` | toxicstream.com | requests + BS4 → MP4直接DL |
| `get_zettai_ero_videos` | zettai-ero.com | requests + BS4 → yt-dlp |
| `get_dmm_videos` | DMM Affiliate API | playwright → MP4直接DL |
| `get_dmm_images` | DMM Affiliate API | requests → 画像直接DL |

### 加工・管理系

| コマンド | 概要 |
|---|---|
| `split_video_as_short` | 動画を15秒ごとに分割し、元の動画と差し替えてDBに再登録する |
| `delete_image_contents` | タイプが画像のコンテンツを全削除する |
| `make_article_thumbnails` | サムネイルがない記事に対して動画の中間フレームを抽出してサムネイルを生成する |
| `calc_series_weight` | `Series.weight` をシリーズ内コンテンツ数に基づいて再計算する |
| `make_series_queue` | `SeriesQueueItem` を全削除して再構築する |
| `make_blog_parts` | backend APIを呼び出してブログパーツHTMLをファイルに保存する |
| `batch_shell` | バッチをインタラクティブに起動・管理するシェル |

---

## コマンド詳細

### get_hime_channel_videos / get_toxicstream_videos / get_zettai_ero_videos

| オプション | 説明 | デフォルト |
|---|---|---|
| `--url URL` | 取得対象のURL | サイトのトップページ |
| `--tag TAG` | タグ名で絞り込む | - |
| `--number N` | 取得する動画数 | 10 |

`--url` と `--tag` は同時に指定できない。

```bash
# URL指定
python manage.py get_hime_channel_videos --url https://hime-channel.com/tag/素人 --number 20

# タグ指定
python manage.py get_toxicstream_videos --tag 素人 --number 10

# デフォルト (トップページから取得)
python manage.py get_zettai_ero_videos --number 5
```

---

### get_dmm_videos / get_dmm_images

DMM Affiliate API を使って動画または画像を取得・保存する。  
`get_dmm_videos` は playwright で商品ページを開いてMP4 URLを抽出してダウンロードする。  
`get_dmm_images` はサムネイル画像とサンプル画像をダウンロードし、サンプル画像群は同一 `series_id` でまとめて登録する。

**事前に必要な環境変数:**

| 変数名 | 説明 |
|---|---|
| `DMM_API_ID` | DMM APIのAPI ID |
| `DMM_AFFILIATE_ID` | DMMのアフィリエイトID |

| オプション | 説明 | デフォルト |
|---|---|---|
| `-k`, `--keyword` | 検索キーワード | (なし) |
| `-s`, `--site` | 検索対象サイト | `FANZA` |
| `-p`, `--params` | 追加APIパラメータ `key:value,...` 形式 | (なし) |
| `-n`, `--number` | 取得する件数 (最大100) | 20 |
| `--of` | 取得開始オフセット | 1 |

```bash
# キーワード指定で画像を取得
python manage.py get_dmm_images -k 素人 -n 50

# サイトとキーワードを指定して動画を取得
python manage.py get_dmm_videos -s FANZA -k 人妻 -n 10

# 追加パラメータで絞り込み
python manage.py get_dmm_images -p "sort:rank,article:actress" -n 30
```

---

### split_video_as_short

DBに登録されている動画を `ffmpeg` で15秒ごとに分割し、  
元コンテンツを削除して分割済みチャンクを同一 `series_id` でDB再登録する。

| オプション | 説明 | デフォルト |
|---|---|---|
| `-n`, `--number` | 処理する動画数 | 全件 |

```bash
python manage.py split_video_as_short -n 10
```

- 15秒以下の動画はスキップされる
- 分割後のファイル名: `<元ファイル名>_part000.mp4`, `_part001.mp4`, ...
- 依存: `ffmpeg`, `ffprobe`

---

### delete_image_contents

`Content.type == TYPE_IMAGE` のレコードを全件削除する。  
実行前に件数を表示し、`--force` なしの場合は確認プロンプトが出る。

| オプション | 説明 |
|---|---|
| `--force` | 確認なしで削除する |

```bash
python manage.py delete_image_contents
python manage.py delete_image_contents --force
```

---

### make_article_thumbnails

`thumbnail` が未設定の `Article` を対象に、紐付いた動画コンテンツからランダムに1本選び、  
`opencv-python` (`cv2`) で動画の中間フレームをJPEGとして抽出してサムネイルに設定する。

| オプション | 説明 |
|---|---|
| `--dry-run` | 実際には保存せず対象記事だけ表示する |

```bash
python manage.py make_article_thumbnails
python manage.py make_article_thumbnails --dry-run
```

- 依存: `opencv-python`
- 保存先: `media/images/thumb_<ランダム8文字>.jpg`

---

### calc_series_weight

`Series.weight` をシリーズ内 `ContentDetail` 数を基に対数スケールで再計算して保存する。

| コンテンツ数 | weight |
|---|---|
| 10未満 | 10.0 (固定) |
| 10以上 | `10 × log10(count)` |

| オプション | 説明 |
|---|---|
| `--dry-run` | 実際には保存せず計算結果だけ表示する |

```bash
python manage.py calc_series_weight
python manage.py calc_series_weight --dry-run
```

---

### make_series_queue

`SeriesQueueItem` を全削除して再構築する。  
`Series.weight` の整数値分だけ各シリーズのキューアイテムを生成し、  
シリーズ未所属のコンテンツは weight=10 相当 (10件) として追加する。

| オプション | 説明 |
|---|---|
| `--dry-run` | 実際には保存せず作成数だけ表示する |

```bash
python manage.py make_series_queue
python manage.py make_series_queue --dry-run
```

`calc_series_weight` → `make_series_queue` の順に実行するショートカット:

```bash
cd website/backend/tools
make_series_queue.bat
```

---

### make_blog_parts

backend の `/api/blog-parts/` エンドポイントを HTTP GET で呼び出し、  
生成された埋め込みHTML をローカルファイルに保存する。

**事前条件**: バックエンドサーバーが起動していること (`python manage.py runserver`)

| オプション | 説明 | デフォルト |
|---|---|---|
| `-o`, `--output` | 出力ファイルパス | `blog_parts.html` |
| `--cols` | 列数 | `3` |
| `--rows` | 行数 | `3` |
| `-k`, `--keyword` | キーワードフィルタ | (なし) |
| `--color` | タイトルバーの背景色 | `#1a1a2e` |
| `--font-color` | タイトルバーの文字色 | `#ffffff` |
| `--tile-size` | タイルの一辺のサイズ (px)、正方形で統一 | `150` |
| `--site-url` | タイルクリック時のリンク先フロントエンドURL | `http://localhost:3000` |
| `--api-url` | APIのベースURL | `http://localhost:8000` |

```bash
# デフォルト設定で blog_parts.html に出力 (150px正方形タイル、3×3)
python manage.py make_blog_parts

# タイルサイズ・グリッドを指定
python manage.py make_blog_parts --tile-size 200 --cols 4 --rows 3

# キーワード・出力先を指定
python manage.py make_blog_parts -o output/blog.html -k 素人 --tile-size 180

# 色・フロントエンドURL・APIサーバーを指定
python manage.py make_blog_parts --color "#003399" --font-color "#eeeeee" \
  --site-url http://example.com --api-url http://192.168.1.10:8000
```

---

### batch_shell

バッチをインタラクティブに起動・管理するシェル。  
デフォルトはバックグラウンド実行で、複数バッチを並行して走らせられる。

```bash
python manage.py batch_shell        # シェルを起動
python manage.py batch_shell --list # バッチ一覧を表示して終了
```

**シェル内コマンド:**

| コマンド | 説明 |
|---|---|
| `help` | バッチ一覧と使い方を表示 |
| `help <batch>` | 指定バッチの引数ヘルプを表示 |
| `run <batch> [args...]` | バックグラウンドでバッチを実行 |
| `run <batch> [args...] --fg` | フォアグラウンドでバッチを実行 |
| `run list` | 実行中ジョブの一覧を表示 |
| `run kill <id>` | 指定ジョブを強制終了 |
| `exit` / `quit` / `q` | シェルを終了 |

```
batch> run get_dmm_images -k 素人          # バックグラウンド実行
batch> run get_dmm_images -k 素人 --fg     # フォアグラウンド実行
batch> run list                            # ジョブ一覧
batch> run kill 1                          # ジョブ ID=1 を強制終了
```

- `readline` が使える環境ではタブ補完が有効
- バックグラウンドジョブの stdout/stderr は破棄される (DEVNULL)
- 依存 (任意): `docopt` — 未インストール時は内蔵の簡易パーサにフォールバック

---

## 保存先

| 種別 | パス |
|---|---|
| 動画ファイル | `website/backend/media/videos/` |
| 画像ファイル | `website/backend/media/images/` |
| データベース | `website/backend/db.sqlite3` (Content, ContentDetail, Tag, Series, SeriesQueueItem, Article モデル) |

---

## 依存ライブラリ

| ライブラリ | 用途 |
|---|---|
| `pyppeteer` | hime-channel (JavaScript描画が必要なページ) |
| `playwright` | get_dmm_videos の動画URL抽出 |
| `requests` | toxicstream / zettai-ero / DMM のHTTPリクエスト |
| `beautifulsoup4` | toxicstream / zettai-ero のHTMLパース |
| `yt-dlp` | zettai-ero の動画ダウンロード (tokyomotion経由) |
| `opencv-python` | make_article_thumbnails のフレーム抽出 |
| `ffmpeg` / `ffprobe` | split_video_as_short の動画分割・再生時間取得 |
| `docopt` | batch_shell の引数パース (任意) |

`pyppeteer` を使用するコマンドは Chrome の実行ファイルが必要。  
パス: `C:\Users\USER\bin\chrome-win\chrome.exe`

`playwright` を使用するコマンドは事前に以下が必要:

```bash
pip install playwright
python -m playwright install chromium
```
