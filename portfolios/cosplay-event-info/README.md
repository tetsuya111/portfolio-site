# コスプレイベント情報まとめサイト（Next.js + Django REST Framework）

ネット上に散らばっているコスプレイベントの予定とコスプレイヤーの情報を、複数のサイトから収集して1か所で検索できるようにした情報まとめサイトです。ポートフォリオとして、**設計（要件定義・設計書・タスク分解）から、スクレイピングのバッチ・重複排除・API・フロントエンド・テストまで**を一通り示すことを目的に作りました。

- **フロントエンド**: Next.js 16（App Router・静的出力）/ React 19 / TypeScript
- **バックエンド**: Django 5.2 / Django REST Framework / SQLite
- **収集バッチ**: Django の管理コマンド / httpx / BeautifulSoup4
- **AI（任意）**: Claude API（公式 SDK `anthropic`）で開催場所を補完・正規化
- **テスト**: pytest + pytest-django / Vitest + Testing Library

## 主な機能

| 機能 | 内容 |
|---|---|
| イベントの検索 | キーワード（イベント名・会場・備考）・期間（開催期間が重なるもの）・都道府県で検索。条件は URL に残るので共有できる |
| イベントの詳細 | 開催日・会場・住所・リンク・備考・取得元の一覧、「Google マップで開く」リンク |
| 地図 | 期間を指定すると、その期間にイベントがある会場を件数付きで一覧表示。選んだ会場を Google マップ（埋め込み）で表示 |
| コスプレイヤーの検索・プロフィール | 名前・説明文・経歴で検索。SNS のリンク・経歴・説明文・取得元を表示 |
| 収集バッチ | 対象サイトからイベント・コスプレイヤーを収集して DB に取り込む |

### 設計上のポイント

- **重複の統合**: 複数サイトに同じイベントが載っていても1件にまとめます。名前を正規化（全角半角・大文字小文字・空白や記号の除去）してから**レーベンシュタイン距離**で類似度（1 − 距離 ÷ 長い方の文字数）を求め、イベントは「類似度 0.85 以上かつ開始日が同じ（開催地の都道府県が異なれば別）」、コスプレイヤーは「類似度 0.9 以上」で同一とみなします。統合時は空の項目を補い、取得元を追加します。距離の計算は依存ライブラリなしの自前実装です。
- **取得ログと再取得の防止**: 取得したページは URL・日時・HTTP ステータス・本文を `FetchedPage` に残し、取得に成功した URL は次回以降取得しません（`--force` で取得し直し）。失敗したページは記録したうえで次回また試します。
- **礼儀正しい収集**: robots.txt で禁止されたパスは取得せず（robots.txt がサーバーエラー・接続不可のときはすべて取得しない）、同じホストへは1秒以上の間隔を空けます。
- **開催場所の正規化**: 主要会場の辞書と都道府県名の抽出によるルールベースの正規化を標準とし、`ANTHROPIC_API_KEY` を設定すると Claude の構造化出力で会場名・都道府県・住所を補完します。AI の結果が不正・通信失敗のときはルールベースの結果を使い、バッチは止まりません。同じ表記は一度しか正規化しません。
- **安全な表示**: 収集した文字列はすべてテキストとして表示し（HTML として解釈しない）、リンクは http(s) のものだけを API・画面の両方で通します。

## ディレクトリ構成

```
cosplay-event-info/
├── package.json            # npm test / lint / build（backend と frontend をまとめて実行）
├── docker-compose.yml      # バックエンドをコンテナで起動（開発・動作確認用）
├── backend/                # Django
│   ├── config/             # 設定・URL
│   ├── catalog/            # モデル・API・管理画面・管理コマンド
│   │   └── collector/      # 収集処理（fetcher・parsers・normalizer・similarity・importer・runner）
│   └── tests/              # pytest（fixtures/ に HTML の固定データ）
├── frontend/               # Next.js（src/app が画面、src/components が部品、src/lib が API クライアントなど）
├── scripts/                # backend の venv を使ってコマンドを実行する補助スクリプト
└── docs/specs/             # requirements.md・design.md・tasks.md
```

## セットアップ

前提: Python 3.12 以上、Node.js 20 以上。

```bash
# バックエンド
cd backend
python -m venv .venv
.venv/bin/pip install -e ".[dev]"        # Windows は .venv\Scripts\pip
cd ..
npm run db:migrate                        # DB（backend/cosplay.db）を作成
npm run seed:demo                         # デモ用の架空のデータを投入（任意）

# フロントエンド
npm --prefix frontend install
```

管理画面（`http://localhost:8000/admin/`）を使う場合は `node scripts/run-backend.mjs manage.py createsuperuser` で管理者を作成します。

## 起動

```bash
npm run dev:backend     # http://localhost:8000（API は /api/ 以下）
npm run dev:frontend    # http://localhost:3000/apps/cosplay-event-info/
```

Docker でバックエンドを起動する場合:

```bash
docker compose up -d --build
docker compose exec backend python manage.py seed_demo
```

## 収集バッチ

```bash
npm run fetch:events                          # 全サイトからイベントを収集
npm run fetch:events -- --site cos-cam        # サイトを指定（複数指定可）
npm run fetch:events -- --force               # 取得済みのページも取得し直す
npm run fetch:cosplayers -- --limit 50        # Wikipedia のカテゴリーからコスプレイヤーを収集（上限50人）
```

- 対象サイト（`--site` に指定する名前）: `cos-cam`（cos-cam.work）・`cos-compass`（cos-compass.com/event/）・`cossuke`（cossuke.jp）・`cospot`（cospot-media.com のイベント一覧）。コスプレイヤーは Wikipedia の「Category:コスプレイヤー」です。
- イベント一覧ページも「取得済み」として扱うため、定期実行で新しい予定を取り込むには `--force` を付けます（cron 等での実行を想定）。コスプレイヤーのカテゴリーページは毎回取得し、人物ページだけを取得済みならスキップします。
- `ANTHROPIC_API_KEY` を設定すると開催場所の正規化に Claude を使います（モデルは既定 `claude-opus-5-5`、`CLAUDE_MODEL` で変更可）。API の利用料金がかかる点に注意してください。
- **収集する前に、各サイトの利用規約と robots.txt を確認してください。** 取得間隔は `FETCH_MIN_INTERVAL`（秒）で長くできます。

### 対象サイトの抽出ルール

イベントは、ページに schema.org の `Event`（JSON-LD）があればそれを使い、なければ `backend/catalog/collector/parsers/events.py` の `SITES` にあるサイトごとの CSS セレクター（`item`・`name_sel`・`link`・`date`・`location`・`notes`）で抽出します。**開発時には対象サイトの HTML 構造を確認していないため、セレクターはブログ形式のサイトで一般的なものを既定にしています。** 実際のサイトで件数が0件になる場合は、ブラウザーの開発者ツールで構造を確認してセレクターを調整してください。日付は「2026年12月5日」「12/5(土)〜12/6(日)」「2026.12.05 - 06」などの表記に対応し、年がない日付は今年とみなし、今日の30日より前になる場合は翌年とみなします。

## API

すべて匿名の GET です（データの追加はバッチと管理画面のみ）。

| エンドポイント | 内容 |
|---|---|
| `GET /api/events/?q=&from=&to=&prefecture=&page=` | イベントの一覧（開始日順・20件ずつ） |
| `GET /api/events/{id}/` | イベントの詳細（取得元つき） |
| `GET /api/venues/?from=&to=` | 期間内にイベントがある会場と件数（既定は今日から30日間） |
| `GET /api/cosplayers/?q=&page=` | コスプレイヤーの一覧（名前順・20件ずつ） |
| `GET /api/cosplayers/{id}/` | コスプレイヤーの詳細（取得元つき） |
| `GET /api/health/` | ヘルスチェック |

## テスト・lint・ビルド

```bash
npm test          # pytest（backend）と Vitest（frontend）
npm run lint      # ruff（check・format）と ESLint・tsc
npm run build     # frontend を静的出力（frontend/out/）
```

テストは実サイト・実 API に接続しません（HTTP は `httpx.MockTransport`、Claude は偽のクライアント、HTML は固定データ）。

## 環境変数

| 変数 | 既定値 | 内容 |
|---|---|---|
| `APP_ENV` | `development` | `production` では `DEBUG` が無効になり、`DJANGO_SECRET_KEY` が必須になる（Dockerfile の既定は `production`） |
| `DJANGO_SECRET_KEY` | （開発用の固定値） | 本番では十分に長いランダムな文字列を設定する。未設定だと本番では起動しない |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | カンマ区切り |
| `DATABASE_PATH` | `backend/cosplay.db` | SQLite ファイルの場所（Docker では `/data/cosplay.db`） |
| `CORS_ORIGINS` | `http://localhost:3000` | API を呼べるオリジン（カンマ区切り） |
| `FETCH_MIN_INTERVAL` | `1.0` | 同じホストへのリクエスト間隔（秒） |
| `ANTHROPIC_API_KEY` | なし | 設定すると開催場所の正規化に Claude を使う（任意） |
| `CLAUDE_MODEL` | `claude-opus-5-5` | 正規化に使う Claude のモデル |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | フロントエンドから呼ぶ API の URL（ビルド時に埋め込まれる） |

空の値は未設定として既定値を使います。

## 本番で動かす場合

- `APP_ENV=production`（Dockerfile の既定）では `DEBUG` が無効になり、`DJANGO_SECRET_KEY` が未設定だと起動しません。`ALLOWED_HOSTS`・`CORS_ORIGINS` も公開するドメインに合わせて設定します。
- フロントエンドは `NEXT_PUBLIC_API_BASE_URL` に API の URL を指定してビルドし、`frontend/out/` を `/apps/cosplay-event-info/` 配下で配信します。
- 管理画面の CSS などの静的ファイルは gunicorn では配信しないため、本番で管理画面を使う場合は `collectstatic` の出力を Web サーバーから配信してください。

## 設計ドキュメント

- [要件定義](docs/specs/requirements.md)
- [設計](docs/specs/design.md)
- [タスク](docs/specs/tasks.md)
