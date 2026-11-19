# AVイベント情報DB（av-event-db）

複数のサイトに散らばっている AV 女優のイベント（サイン会・撮影会など）の告知を、バッチで1つのDBに集めて検索・地図表示できるようにする情報サイトです。ポートフォリオ用のプロジェクトです。

- バックエンド: Django REST Framework（SQLite）。取り込みバッチを管理コマンドとして同梱
- フロントエンド: Next.js（App Router・静的出力、`/apps/av-event-db` 配下で配信）

要件・設計・タスクは [docs/specs/](docs/specs/) を参照してください（[requirements.md](docs/specs/requirements.md)・[design.md](docs/specs/design.md)・[tasks.md](docs/specs/tasks.md)）。

## 主な機能

- 対象サイトの一覧ページからイベント詳細を辿って取り込む（`fetch_events`）
- 取得したページを DB に記録し、取得済みの詳細ページは再取得しない（robots.txt を守り、同じサイトへは1秒以上あける）
- 開催日が同じでイベント名のレーベンシュタイン距離による類似度が 0.8 以上なら同一イベントとして統合する
- 開催場所を Claude API で補完・正規化し、Google Geocoding API で緯度経度を求める（キーがなければ規則ベースの正規化だけを行う）
- キーワード・期間・都道府県での検索、詳細表示、期間指定での地図表示
- 初回表示時の年齢確認（18歳以上）

画像・動画は扱わず、告知のテキスト情報だけを掲載します。

## セットアップ

Python 3.12 以上と Node.js が必要です。

```bash
cd portfolios/av-event-db

# バックエンド
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -e "backend[dev]"   # macOS/Linux は backend/.venv/bin/python
npm run db:migrate

# フロントエンド
npm --prefix frontend install
```

## 起動

```bash
npm run seed:demo      # 画面確認用の架空のデモデータを入れる（任意）
npm run dev:backend    # http://localhost:8000
npm run dev:frontend   # http://localhost:3000/apps/av-event-db/
```

開発サーバーは `http://localhost:3000/apps/av-event-db/` か `http://127.0.0.1:3000/apps/av-event-db/` で開いてください。それ以外のホスト（LAN の IP など）で開くと、Next.js が JS の読み込みを拒否してボタンなどが動かなくなります。その場合は `NEXT_DEV_ALLOWED_ORIGINS` にホストを指定してから起動し直してください。

## イベントの取り込み

```bash
npm run fetch:events                               # すべての対象サイト
npm run fetch:events -- --source av-event          # サイトを指定（複数可）
npm run fetch:events -- --source pls1 --limit 10   # サイトごとに新しく取得するページ数を制限
npm run fetch:events -- --retry-unparsed          # 抽出ルールを直したあと、抽出できなかったページを取り直す
```

サイトごとに「作成 / 統合 / スキップ / 失敗」の件数を出力します。定期実行したい場合は cron などからこのコマンドを呼んでください。取得したページは `FetchedPage`（Django admin では「取得ページ」）に残ります。通信に失敗したページは次回の実行で取り直し、取得できたのにイベント名・開催日を抽出できなかったページ（「解析できず」）は `--retry-unparsed` を付けたときだけ取り直します。

### 抽出ルールの調整

対象サイトと CSS セレクタは [backend/events/crawler/sources.json](backend/events/crawler/sources.json) にまとめています。`av-event` は実サイトの HTML に合わせて調整済みです。**`dmm-avevent`・`pls1` のセレクタは HTML を確認せずに置いた仮の値**なので、取り込む前に調整してください。コードの変更は不要です。

抽出に失敗したページは、`[サイト名] イベント名を抽出できませんでした（title: <セレクタ>）: <URL>` のように理由と使ったセレクタがログ（標準エラー）に出ます。セレクタを直したら `--retry-unparsed` を付けて取り直してください。

| 項目 | 内容 |
|---|---|
| `name` | サイト名（`--source` で指定する名前） |
| `list_urls` | 毎回取得する一覧ページ |
| `mode` | `detail`（一覧から詳細ページを辿る）か `list`（一覧の各項目から直接読む） |
| `detail_link_selector` | `detail` のとき、一覧から詳細ページへのリンク（`a` 要素）を選ぶセレクタ |
| `item_selector` | `list` のとき、1件分の要素を選ぶセレクタ |
| `cookies` | 送る Cookie（年齢確認が必要なサイト用）。`list_urls` と同じオリジン（スキーム＋ホスト）へのリクエストにだけ送る |
| `fields` | `title`・`date` は必須。ほかに `actresses`・`venue`・`address`（会場名と連結して開催場所にする）・`summary`・`note`・`link`。文字列（セレクタ）か `{"selector", "multiple", "attr"}`。単一値のフィールドは、一致した要素のうち最初の空でないものを使う |

日付は `2026年12月3日`・`2026/12/3`・`12/3(木)`・`12月3日`・`〜` 区切りの期間などに対応しています。

## 環境変数

バックエンドの値は `backend/.env` に書けます（[backend/.env.example](backend/.env.example) をコピーして使う）。シェルで設定した環境変数があればそちらが優先されます。フロントエンドの `NEXT_PUBLIC_*` は `frontend/.env.local` に書きます。どちらもコミットされません。

| 変数 | 用途 | 既定値 |
|---|---|---|
| `APP_ENV` | `development`（DEBUG 有効）・`test`・それ以外は本番扱い（DEBUG 無効・`DJANGO_SECRET_KEY` 必須） | 本番扱い（`npm run` 経由のときは `development`） |
| `DJANGO_SECRET_KEY` | 本番では必須 | 開発用の固定値 |
| `ALLOWED_HOSTS` | カンマ区切り | `localhost,127.0.0.1` |
| `CORS_ORIGINS` | フロントエンドのオリジン（カンマ区切り） | `http://localhost:3000,http://127.0.0.1:3000` |
| `DATABASE_PATH` | SQLite のファイル | `backend/db.sqlite3` |
| `DJANGO_ENABLE_ADMIN` | `1` で `/admin/` を有効にする | 無効 |
| `FETCH_MIN_INTERVAL` | 同じサイトへのリクエスト間隔（秒） | `1.0` |
| `ANTHROPIC_API_KEY` | 開催場所の AI 補完（未設定なら規則ベース） | なし |
| `VENUE_NORMALIZER_MODEL` | AI 補完に使う Claude のモデル | `claude-opus-5-5` |
| `GOOGLE_MAPS_GEOCODING_API_KEY` | 会場の緯度経度の取得（バックエンド） | なし |
| `NEXT_DEV_ALLOWED_ORIGINS` | 開発サーバーを localhost・127.0.0.1 以外のホスト（LAN の IP など）で開くときに許可するホスト（カンマ区切り）。`CORS_ORIGINS` にも同じオリジンを追加する | なし |
| `NEXT_PUBLIC_API_BASE_URL` | フロントエンドから呼ぶ API の場所（ビルド時） | `http://localhost:8000` |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | 地図表示用の Maps JavaScript API キー（ビルド時。未設定なら会場一覧で表示） | なし |

`NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` はブラウザに配信されるため、Google Cloud のコンソールで HTTP リファラーと Maps JavaScript API に利用を制限したキーを使ってください。

## API

| パス | 内容 |
|---|---|
| `GET /api/health/` | ヘルスチェック |
| `GET /api/events/?q=&from=&to=&prefecture=&page=` | イベント一覧（開催日順・20件ごと） |
| `GET /api/events/{id}/` | イベント詳細（取得元リンクを含む） |
| `GET /api/map/venues/?from=&to=` | 期間内にイベントがある会場（既定は今日から30日間、最大366日） |

API は読み取り専用です。DB への追加は取り込みバッチだけが行います。

## テスト・lint・ビルド

```bash
npm test        # pytest + Vitest
npm run lint    # ruff（check・format）+ ESLint・tsc
npm run build   # frontend/out に静的出力
```

外部サービス（対象サイト・Claude API・Google API）への通信はテストではすべてモックしています。
