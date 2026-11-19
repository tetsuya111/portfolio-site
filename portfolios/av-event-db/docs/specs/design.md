# 設計: AVイベント情報DBサイト（av-event-db）

要件: [requirements.md](requirements.md) ／ タスク: [tasks.md](tasks.md)

## TL;DR

Django REST Framework のバックエンドに、対象サイトをクロールしてイベントを取り込む管理コマンド `fetch_events` を同梱する。取り込み時に取得ページをDBへ記録して詳細ページの再取得を防ぎ、レーベンシュタイン距離で重複イベントを統合し、開催場所を Claude API で正規化・Google Geocoding API で座標化する。Next.js（静的出力）のフロントエンドは読み取り専用APIを呼び、検索画面・詳細画面・期間指定の地図画面を提供する。

## Non-Goals（技術面）

- 認証・書き込みAPI（DBへの追加は管理コマンドのみ）
- JavaScript 実行が必要なページのクロール（ヘッドレスブラウザは使わない）
- 全文検索エンジン（想定件数が数千件規模のため、DBの `icontains` 検索で足りる）
- 定期実行の仕組み（cron 等から `npm run fetch:events` を呼ぶ運用に任せる）

## 全体構成

```
portfolios/av-event-db/
├── package.json                 # test / lint / build などをまとめる（backend の .venv を使う）
├── scripts/run-backend.mjs      # backend/.venv の Python でコマンドを実行する
├── backend/                     # Django + DRF（SQLite）
│   ├── config/                  # settings・urls
│   └── events/
│       ├── models.py            # Actress / Venue / VenueAlias / Event / EventSource / FetchedPage
│       ├── serializers.py, views.py, urls.py   # 読み取り専用API
│       ├── crawler/
│       │   ├── sources.json     # 対象サイトごとの抽出ルール（NFR-4）
│       │   ├── sources.py       # 設定の読み込み・検証
│       │   ├── fetcher.py       # HTTP取得・robots.txt・間隔制御・ページログ
│       │   ├── parser.py        # セレクタに従ってHTML→RawEvent
│       │   ├── dates.py         # 日付文字列の解析
│       │   ├── dedupe.py        # レーベンシュタイン距離・重複判定
│       │   ├── venues.py        # 会場の正規化（AI/規則）・ジオコーディング
│       │   └── importer.py      # RawEvent→DB（新規作成 or 統合）
│       └── management/commands/
│           ├── fetch_events.py  # 取り込みバッチ
│           └── seed_demo.py     # デモデータ投入
└── frontend/                    # Next.js App Router（output: export）
    └── src/
        ├── app/                 # / （検索）・/events/?id= （詳細）・/map/ （地図）
        ├── components/          # AgeGate / EventSearch / EventDetail / EventMap など
        └── lib/                 # api.ts・types.ts・url.ts
```

既存の `portfolios/inventory-management/` と同じく、ルートの `package.json` から `scripts/run-backend.mjs` 経由で backend の `.venv` を呼ぶ構成にそろえる。

## データモデル

| モデル | 主な項目 | 用途・対応要件 |
|---|---|---|
| `Actress` | `name`（一意） | 参加女優（REQ-1.2） |
| `Venue` | `name`・`address`・`prefecture`・`latitude`・`longitude`（`name`+`address` で一意） | 正規化済みの会場（REQ-4） |
| `VenueAlias` | `raw_text`（一意）→ `venue` | 取り込み時の生の場所文字列と会場の対応。同じ文字列でAIを再度呼ばない（REQ-4.2） |
| `Event` | `title`・`normalized_title`・`start_date`・`end_date`・`start_time`・`url`・`venue`・`raw_venue`・`summary`・`note`・`actresses`(M2M) | イベント（REQ-1.2） |
| `EventSource` | `event`・`source_name`・`source_url`（一意） | 取得元リンク。統合時に複数持つ（REQ-3.2） |
| `FetchedPage` | `url`（一意）・`source_name`・`kind`（list/detail）・`status_code`・`body`・`content_hash`・`result`（success/failed/disallowed）・`error`・`fetched_at` | 取得ページのログ（REQ-2） |

- 開催期間は `start_date`〜`end_date`（単日なら同じ日）で表す。`end_date >= start_date` をモデルの検証で保証する。
- `normalized_title` は重複判定用（NFKC・小文字化・空白と記号の除去）。保存時に自動計算する。
- `(start_date)` と `(venue, start_date)` にインデックスを張る（NFR-1）。

## 取り込みバッチ（REQ-1・REQ-2）

`python manage.py fetch_events [--source <name> ...] [--limit N] [--sources-file <path>]`

1. `sources.json` を読み、`--source` 指定があれば絞り込む（REQ-1.3）。
2. 各サイトの `list_urls` を取得する（一覧ページは毎回取得し、ログは残す）。
3. `mode` に応じて処理する。
   - `detail`: 一覧から `detail_link_selector` でリンクを集め、各詳細ページを取得して `fields` で抽出する。
   - `list`: 一覧ページの `item_selector` の各要素から直接 `fields` で抽出する（詳細ページのないサイト向け）。
4. 抽出結果（`RawEvent`）を `importer.import_event()` に渡す。
5. 最後に件数（作成・統合・スキップ・失敗）を出力する。

### 抽出ルール（`sources.json`）

```json
{
  "name": "av-event-new",
  "base_url": "https://www.av-event.jp",
  "list_urls": ["https://www.av-event.jp/new_event/"],
  "mode": "detail",
  "detail_link_selector": "a[href*='/event/']",
  "item_selector": null,
  "cookies": {},
  "fields": {
    "title": "h1",
    "actresses": {"selector": ".actress a", "multiple": true},
    "date": ".event-date",
    "venue": ".event-place",
    "summary": ".event-summary",
    "note": ".event-note",
    "link": {"selector": "a.official-link", "attr": "href"}
  }
}
```

- フィールドは文字列（CSSセレクタ・最初の要素のテキスト）か、`selector`／`multiple`／`attr` を持つオブジェクト。
- DMM のように年齢確認Cookieが必要なサイトは `cookies` に設定する。
- 対象サイトの実HTMLは未調査のため、同梱する `sources.json` のセレクタは仮置き。実サイトに合わせてこのファイルだけを直せばよい（NFR-4）。

### HTTP取得（`fetcher.py`）

- `httpx.Client` を使い、User-Agent は汎用名 `av-event-db-crawler/0.1` とする。タイムアウト10秒。
- ホストごとに最後のリクエスト時刻を持ち、1秒未満なら待つ（REQ-1.5）。待機関数は差し替え可能にしてテストで時間を使わない。
- `urllib.robotparser` でオリジンごとの robots.txt を1回だけ読み、禁止URLは `result=disallowed` で記録して取得しない（REQ-1.6）。RFC 9309 に沿い、robots.txt のリダイレクトは辿り、4xx は制限なし、5xx・通信エラーはすべて禁止とみなす。
- リダイレクトは自動では辿らず1回ずつ処理し（最大5回）、リダイレクト先も robots.txt で確認する。設定の Cookie は元のURLと同じホストにだけ送る。
- 500文字を超えるURLは保存できないため扱わない。
- `fetch(url, kind)`:
  - `kind=detail` かつ `FetchedPage(url, result=success)` があれば `None` を返し、HTTPを送らない（REQ-2.2）。失敗記録なら再取得する（REQ-2.3）。
  - 取得後、URL・ステータス・本文・SHA-256・結果を `FetchedPage` に upsert する（REQ-2.1）。
  - 例外・4xx/5xx は `result=failed` と `error` を記録して `None` を返す（REQ-1.4）。

### 日付の解析（`dates.py`）

`2026年11月23日`・`2026/11/23`・`2026-11-23`・`11/23(土)`・`11月23日` に対応し、`〜`／`~`／`-` 区切りでつながる2つ目の日付だけを終了日とする（「※予約受付は11/10から」のような無関係な日付は使わない）。年がない場合は取得日の年とし、取得日より60日以上前になる場合は翌年とする。時刻 `HH:MM` があれば最初のものを `start_time` にする。日付が読めないイベントは取り込まずスキップとして数える。

## 重複判定と統合（`dedupe.py`・`importer.py`、REQ-3）

- `levenshtein(a, b)`: 2行DPで計算する（O(len(a)·len(b))、タイトルは短いので十分）。
- `similarity(a, b) = 1 - levenshtein(a, b) / max(len(a), len(b))`（両方空なら1）。
- `find_duplicate(raw)`:
  1. 同じ `source_url` の `EventSource` があればそのイベント（同ページの再取り込み）。
  2. `start_date` が同じイベントのうち、`normalized_title` の類似度が最大かつ **0.8 以上** のもの（REQ-3.1）。開催日が違えば候補にならない（REQ-3.4）。
- 統合（`merge_into`）: `EventSource` を追加し（REQ-3.2）、空の `url`・`summary`・`note`・`venue`・`start_time`・`end_date` を補い、女優を和集合にする（REQ-3.3）。既存の値は上書きしない（先に取り込んだサイトを優先する）。
- しきい値 0.8 は「【】付きの装飾違い」「全角半角違い」「末尾に会場名が付く」程度を同一と見なせる値として選んだ。定数にしてテストで境界を確認する。
- 「第1部／第2部」は1文字違いで類似度が高くなるため、両方のタイトルに部番号（`N部`、漢数字を含む）があって番号が違う場合や、両方に開始時刻があって違う場合は、類似度にかかわらず別イベント（同じ日の別の回）とする。
- 一覧（`list`）モードの取得元は、複数の項目が同じリンクを指すことがあるため、リンクではなく「一覧URL＋項目内容のハッシュ」で識別する。

## 会場の正規化（`venues.py`、REQ-4）

`resolve_venue(raw_text) -> Venue | None`

1. 規則ベースの前処理（NFKC・連続空白の統一・前後の空白除去）。空なら `None`。
2. `VenueAlias` に前処理後の文字列があればその会場を返す（AIを呼ばない）。
3. ノーマライザで `{name, address, prefecture}` を得る。
   - `ClaudeVenueNormalizer`: `ANTHROPIC_API_KEY` があるとき使う。モデルは環境変数 `VENUE_NORMALIZER_MODEL`（既定 `claude-opus-5-5`、`effort: low`）。構造化出力（JSON Schema）で、会場名・住所・都道府県を補完させる。JSONとして読めない・API例外のときは規則ベースにフォールバックする（REQ-4.3）。
   - `RuleVenueNormalizer`: 前処理後の文字列を `name` とし、文字列中の都道府県名を `prefecture` に入れる。
4. `name`+`address` で `Venue` を get_or_create（REQ-4.2）し、`VenueAlias` を作る。
5. 会場に座標がなく `GOOGLE_MAPS_GEOCODING_API_KEY` があれば Google Geocoding API で緯度経度を取得する（REQ-4.4）。失敗しても会場は保存し、次回のバッチ実行で再試行する（同じ実行内では1会場1回まで）。
6. 会場の解決（AI・ジオコーディングの通信）はイベント保存のトランザクションの外で行い、SQLite のロックを長く持たない。

ノーマライザとジオコーダはインターフェース（`normalize(text)`・`geocode(query)`）で差し替え可能にし、テストではフェイクを渡す。

## API（読み取り専用、NFR-2）

| メソッド・パス | 内容 | 要件 |
|---|---|---|
| `GET /api/health/` | `{"status": "ok"}` | — |
| `GET /api/events/` | 一覧。`q`・`from`・`to`・`prefecture`・`page` で絞り込み、`start_date, start_time, id` 昇順、20件ごと | REQ-5.1〜5.4, 5.6 |
| `GET /api/events/{id}/` | 詳細（会場・女優・取得元リンクを含む） | REQ-5.5 |
| `GET /api/map/venues/?from=&to=` | 期間内にイベントがある会場と、その会場の期間内イベント | REQ-6.1〜6.3 |

- `q`: `title`／`summary`／`note`／`actresses__name`／`venue__name` の `icontains` を OR で結合し `distinct()`。
- `from`・`to`（`YYYY-MM-DD`）: 期間の重なり（`start_date <= to` かつ `end_date >= from`）。不正な日付は 400。
- 地図API は `from`・`to` 未指定時、今日〜30日後とする。期間が366日を超える指定は 400（過大な応答を防ぐ）。
- DRF は `ReadOnlyModelViewSet`・`JSONRenderer` のみ。CORS は `django-cors-headers` で `CORS_ALLOWED_ORIGINS`（環境変数）だけ許可する。

## フロントエンド

Next.js App Router・`output: "export"`・`basePath: "/apps/av-event-db"`。APIの場所は `NEXT_PUBLIC_API_BASE_URL`（既定 `http://localhost:8000`）。静的出力のため詳細画面は動的ルートではなく `/events/?id=<id>` とする。

| 画面 | 内容 | 要件 |
|---|---|---|
| 共通 `AgeGate` | `localStorage` の `av-event-db:age-confirmed` がなければ確認画面だけを表示。「18歳以上です」で保存して内容を表示、「18歳未満です」で内容を表示しないまま案内文を出す | REQ-7 |
| `/` 検索 | キーワード・開始日・終了日・都道府県のフォーム、結果一覧（日付・イベント名・女優・会場）、前後ページ、該当なし表示。条件はURLクエリに反映 | REQ-5.1〜5.4, 5.6, 5.7 |
| `/events/?id=` 詳細 | 全項目と取得元リンク一覧、会場のGoogle マップ検索リンク | REQ-5.5 |
| `/map/` 地図 | 期間フォーム（既定: 今日〜30日後）。`NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` があれば Maps JavaScript API を `<script>` で読み込んでピン表示、ピン選択で会場のイベント一覧。座標なし会場とキー未設定時はGoogle マップ検索リンク付きの一覧 | REQ-6 |

- 取得したテキストは React のテキストとして描画し、`dangerouslySetInnerHTML` を使わない（NFR-3）。
- 外部リンクは `safeExternalUrl()` で `http:`/`https:` 以外を捨て、`rel="noopener noreferrer"` を付ける（NFR-3）。
- Google マップの検索リンクは `https://www.google.com/maps/search/?api=1&query=<会場名 住所>`。

## 横断的関心事

### セキュリティ・プライバシー

- 書き込みAPIなし・認証なし（公開情報の閲覧のみ）。Django admin は `DJANGO_ENABLE_ADMIN=1` のときだけURLに載せる。
- `SECRET_KEY`・`DEBUG`・`ALLOWED_HOSTS`・APIキーは環境変数。`APP_ENV` 未設定時は本番扱い（DEBUG 無効）とし、本番で `SECRET_KEY` 未設定なら起動を止める。ローカル開発用の npm スクリプトだけが `APP_ENV=development` を補う。
- クローラが取得したHTMLはテキスト抽出のみに使い、そのまま配信しない。リンクは `http(s)` のみ保存する。
- 個人情報: 女優名は対象サイトで公開されている芸名のみ。閲覧者の情報は保存しない（年齢確認の回答もブラウザ内のみ）。

### パフォーマンス・スケーラビリティ

想定は数千件。日付インデックスとページ分割（20件）、一覧APIの `select_related("venue")`・`prefetch_related("actresses")` でN+1を避ける。1,000件のテストデータで応答時間を確認するテストを置く（NFR-1）。

### オブザーバビリティ

`fetch_events` はサイトごとに作成・統合・スキップ・失敗件数を標準出力に出し、失敗ページは `FetchedPage.error` に残る。API は Django 標準のログに任せる。

### テスト戦略

- バックエンド（pytest + pytest-django）: 日付解析・レーベンシュタイン・類似度しきい値・パーサ（HTMLフィクスチャ）・fetcher（`httpx.MockTransport`）・importer（統合／別イベント）・会場解決（フェイクのノーマライザ・ジオコーダ）・API（絞り込み・ページ分割・400）・管理コマンド（フェイク fetcher）。外部通信はすべてモック。
- フロントエンド（Vitest + Testing Library）: AgeGate、検索フォームとURLクエリ、一覧と該当なし、詳細、地図のフォールバック一覧、`safeExternalUrl`。
- lint: ruff（check・format）、ESLint・`tsc --noEmit`。

### ロールアウト計画

新規プロジェクトのため既存機能への影響なし。`npm run db:migrate` でDBを作成し、`npm run seed:demo` でデモデータ、`npm run fetch:events` で実データを取り込む。ロールバックはディレクトリ単位で削除できる。

## 既存アーキテクチャとの整合性

- 構成・スクリプト名・ruff 設定は `portfolios/inventory-management/` と、同じく DRF を使う別ブランチの cosplay-event-info にそろえた。
- 静的出力の `basePath` を固定値で書くのは、portfolio-importer が直書きを検出するという inventory-management の方針に合わせた。

## 検討した代替案

- **レーベンシュタイン距離にライブラリ（rapidfuzz 等）を使う** — タイトルは短く件数も少ないため自前実装で十分。依存を増やさず、距離の定義をテストで固定できる方を採った。
- **サイトごとにパーサクラスを書く** — 実HTML未調査の段階でコードに埋め込むと調整のたびに修正が要る。設定ファイル駆動にした（NFR-4）。
- **Scrapy を使う** — 対象は5ページ程度で、robots.txt と間隔制御は自前で数十行で書ける。テストしやすい httpx + BeautifulSoup を採った。
- **地図の座標をブラウザ側の Geocoder で毎回求める** — 表示のたびにAPI呼び出しが増え、キーの利用範囲も広がる。取り込み時に一度だけ求めてDBに保存する方式を採った。
- **ページの再取得防止を本文ハッシュの一致で判定する** — 判定にリクエストが必要になり負荷削減にならない。URL単位で取得済みを判定する。
- **PostgreSQL を使う** — 想定件数が小さく、既存の backend-compose が SQLite ボリュームに対応しているため SQLite を採った。
