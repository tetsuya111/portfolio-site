# 設計: コスプレイベント情報まとめサイト（cosplay-event-info）

要件: [requirements.md](requirements.md) ／ タスク: [tasks.md](tasks.md)

## TL;DR

`portfolios/cosplay-event-info/` に、Django REST Framework（読み取り専用 API とスクレイピングのバッチ）と Next.js（静的出力のフロントエンド）からなる情報まとめサイトを新規作成する。バッチは取得したページを `FetchedPage` に記録して再取得を防ぎ、名前のレーベンシュタイン類似度で重複を統合し、開催場所は AI（任意）またはルールで正規化して `Venue` にまとめる。フロントエンドはイベント・コスプレイヤーの検索と、期間で絞った会場を Google マップの埋め込みで表示する。

## Non-Goals（技術面）

- 認証・認可（API はすべて匿名の GET のみ。書き込みは Django 管理画面とバッチだけ）
- JavaScript の実行が必要なサイトの収集（ヘッドレスブラウザーは使わない）
- 収集の並列化・分散実行（1プロセスで順番に取得する）
- 会場の緯度経度の保存・複数マーカーの地図表示

## 全体構成

```
portfolios/cosplay-event-info/
├── package.json              # npm test / lint / build（backend と frontend をまとめて実行）
├── scripts/run-backend.mjs   # backend/.venv の Python でコマンドを実行する
├── docker-compose.yml        # バックエンドをコンテナで起動（開発用）
├── backend/                  # Django + DRF
│   ├── config/               # settings・urls・wsgi
│   ├── catalog/              # モデル・API・管理画面・管理コマンド
│   │   ├── collector/        # 収集処理（取得・抽出・正規化・重複統合）
│   │   └── management/commands/  # fetch_events / fetch_cosplayers / seed_demo
│   └── tests/
└── frontend/                 # Next.js（App Router・output: "export"）
```

既存の [inventory-management](../../../inventory-management/) と同じ構成（ルートの npm スクリプトから backend・frontend をまとめて実行、`scripts/run-backend.mjs`、Windows 対策の `run-vitest.mjs`、`basePath` の固定値）にそろえる。違いはバックエンドが FastAPI ではなく Django/DRF である点で、これは要望で指定されている。

```
[対象サイト] --httpx--> Fetcher --FetchedPage(ログ)--> Parser --> Normalizer --> Importer(重複統合) --> SQLite
                                                                                                    |
                                    Next.js（静的） <--JSON-- DRF（ReadOnly API） <------------------+
```

## データモデル（catalog/models.py）

| モデル | 項目 | 備考 |
|---|---|---|
| `FetchedPage` | `url`(unique), `kind`(`event`/`cosplayer`), `status_code`(null可), `content`(text), `error`(text), `fetched_at` | FT-1。`status_code` が 200〜299 のものを「取得済み」とする |
| `Venue` | `name`(unique), `prefecture`, `address` | EV-4。正規化後の会場。地図の単位 |
| `Event` | `name`, `url`, `location_raw`, `venue`(FK, null可), `start_date`, `end_date`, `notes`, `source_url`, `sources`(M2M→FetchedPage), `created_at`, `updated_at` | EV-1。`start_date` に索引。`end_date >= start_date` を CHECK 制約で保証 |
| `Cosplayer` | `name`, `sns_links`(JSON: URL の配列), `career`, `description`, `notes`, `source_url`, `sources`(M2M→FetchedPage), `created_at`, `updated_at` | CP-1 |

`source_url` は最初に見つけた取得元、`sources` は統合されたすべての取得元（EV-11・CP-5 の「取得元リンクの一覧」）。

## 収集処理（catalog/collector/）

### Fetcher（fetcher.py）— FT-1〜FT-4、NF-1

- `Fetcher(client: httpx.Client, *, min_interval=1.0, sleep=time.sleep, clock=time.monotonic)`。テストでは `httpx.MockTransport` と偽の `sleep` を渡す。
- `fetch(url, kind, *, force=False) -> FetchedPage | None`
  - 取得済み（成功ステータスの `FetchedPage` がある）かつ `force=False` なら `None` を返し、通信しない（FT-2・FT-3）。
  - robots.txt をホストごとに1回取得し `urllib.robotparser` で判定。禁止なら取得せず `None`（NF-1）。robots.txt が 4xx なら制限なし、5xx・接続できない場合はすべて禁止とみなす（RFC 9309）。
  - 同じホストへの前回リクエストから `min_interval` 秒未満なら待つ（NF-1）。リダイレクトは自前でたどり（最大5回）、リダイレクト先のホストでも robots.txt と間隔を守る。
  - `None` を返した理由（取得済み・禁止・失敗）は `last_outcome` に残し、バッチの件数集計に使う。
  - 結果（成功・失敗とも）を `FetchedPage` に保存（`update_or_create`）。ただし `--force` の再取得に失敗した場合は、前回の本文を残して `error` だけ更新する。通信例外・4xx/5xx は `error` に記録し `None` を返す（FT-4）。
- User-Agent は汎用名 `cosplay-event-info-bot/0.1`（個人情報を含めない）。

### 抽出（parsers/）

- **events.py**（EV-1）
  - `parse_jsonld_events(html, base_url)`: （日時は時差を考慮して日本時間の日付にする）`script[type="application/ld+json"]` から `@type` が `Event`（配列・`@graph` も探索）のものを `EventItem(name, url, location, start_date, end_date, notes)` に変換。
  - `parse_with_selectors(html, base_url, config, today)`: `SiteConfig`（`item`・`name`・`link`・`date`・`location`・`notes` の CSS セレクター）で抽出。
  - `parse_events(html, base_url, config, today)`: JSON-LD で1件以上取れればそれを、なければセレクターの結果を返す。名前・開始日がない項目は捨てる。
  - `parse_date_range(text, today)`: 「2026年12月5日」「2026/12/5」「12/5(土)〜12/6(日)」「2026.12.05 - 06」などから開始日・終了日を返す。年がなければ今年とし、`today` の30日より前になる場合は翌年を補う（一覧に残っている直近の過去のイベントを翌年と誤解しないため）。
  - `SITES`: 対象4サイト（cos-cam・cos-compass・cossuke・cospot）の `SiteConfig`。セレクターは汎用的な候補（`article`、`.event` など）で、実サイトの構造に合わせて調整する前提（requirements の仮定を参照）。
- **cosplayers.py**（CP-1）
  - `parse_category_page(html, base_url) -> (person_urls, next_page_url)`: MediaWiki のカテゴリーページ（`#mw-pages` 内のリンク、「次のページ」リンク）。
  - `parse_person_page(html, url) -> CosplayerItem`: 名前は `#firstHeading`、説明文は本文の最初の段落、経歴は見出しに「経歴」「来歴」「略歴」「人物」を含む節の本文、SNS は情報欄（infobox）と「外部リンク」節のリンクのうち X/Twitter・Instagram・YouTube・TikTok・Facebook・Threads のホストのもの（本文・脚注のリンクは他人や報道のアカウントがあるため含めない）。本文は `#mw-content-text` 内に限定し、「[編集]」リンクは除く。脚注記号 `[1]` は除去。見出しは旧形式（`h2`）と新形式（`div.mw-heading > h2`）の両方に対応。

### 正規化（normalizer.py）— EV-4〜EV-6

- `NormalizedLocation(venue_name, prefecture, address)`。
- `RuleBasedNormalizer`: NFKC 正規化・空白の圧縮・括弧内の補足の除去、主要会場の辞書（東京ビッグサイト・幕張メッセ・インテックス大阪・ポートメッセなごや・池袋サンシャインシティ など。別名を含む）、47都道府県名の抽出。
- `ClaudeNormalizer(client, fallback, model)`: 公式 SDK（`anthropic`）で Claude Messages API（既定 `claude-opus-5-5`、環境変数 `CLAUDE_MODEL` で変更可、`effort: low`）に生の場所文字列を渡し、構造化出力（`output_config.format` の JSON Schema）で `venue_name`・`prefecture`・`address` を返させる。都道府県が47件のいずれでもない場合・JSON が壊れている場合・通信失敗時は `fallback`（ルールベース）の結果を返す（EV-6）。
- `get_normalizer()`: 環境変数 `ANTHROPIC_API_KEY` があれば `ClaudeNormalizer`、なければ `RuleBasedNormalizer`（EV-5）。
- 同じ `location_raw` の結果はバッチ実行中メモリーにキャッシュし、DB に同じ `location_raw` のイベントがあればその `Venue` を再利用して API 呼び出しを減らす。

### 重複統合（similarity.py・importer.py）— EV-3・CP-3

- `levenshtein(a, b)`: 2行の DP による標準実装（依存ライブラリなし）。
- `normalize_name(s)`: NFKC → 小文字化 → 空白・記号（`・`、`-`、`!` など）の除去。
- `similarity(a, b) = 1 - levenshtein(na, nb) / max(len(na), len(nb))`（両方空なら 0）。
- `import_event(item, page, normalizer)`: 同じ `start_date` のイベント（開催地の都道府県がどちらも判明していて異なるものは除く）を候補に、類似度 0.85 以上で最大のものに統合（空の項目を補う・`sources` に追加）。なければ新規作成。結果を `created`/`merged` で返す。
- `import_cosplayer(item, page)`: 名前の長さの差が `ceil(長い方×0.1)` 以内の候補に絞ってから類似度 0.9 以上で統合。SNS は URL を重複なく追加。
- しきい値は `settings.EVENT_SIMILARITY_THRESHOLD`・`COSPLAYER_SIMILARITY_THRESHOLD` で変更できる。

### バッチ（management commands）— EV-2・CP-2

- `python manage.py fetch_events [--site <name>] [--force]`: `SITES` の開始 URL を取得 → 抽出 → 正規化 → 統合。サイトごとに件数（取得・新規・統合・スキップ）を出力。
- `python manage.py fetch_cosplayers [--limit N] [--force]`: カテゴリーページ（`--force` に関係なく毎回取得する一覧と、取得済みをスキップする個人ページを区別するため、カテゴリーページは常に `force=True`）を次ページまでたどり、個人ページを取得（取得済みはスキップ）→ 抽出 → 統合。
  - イベントの開始 URL も「一覧ページ」だが、要件の仮定どおり既定では再取得しない（`--force` で再取得）。
- `python manage.py seed_demo`: 通信なしでデモ用のイベント・会場・コスプレイヤーを投入（ポートフォリオの閲覧用。冪等）。
- cron 等での定期実行を想定し、終了コードは「全サイトで取得失敗」のときだけ 1。

## API（DRF、すべて GET・匿名）

| エンドポイント | 内容 | 要件 |
|---|---|---|
| `GET /api/health/` | `{"status": "ok"}` | — |
| `GET /api/events/?q=&from=&to=&prefecture=&page=` | 開始日昇順・1ページ20件。`q` は名前・`location_raw`・会場名・備考の部分一致（OR）。期間は `start_date <= to` かつ `end_date >= from`（重なり）。不正な日付は 400 | EV-7〜EV-10, NF-2 |
| `GET /api/events/{id}/` | 全項目＋`venue`＋`sources`（URL・取得日時） | EV-11 |
| `GET /api/venues/?from=&to=` | 期間内のイベントがある会場と件数（件数の降順、最大200件）。各会場に該当イベントの id・名前・日付も含める | MAP-1 |
| `GET /api/cosplayers/?q=&page=` | 名前の昇順・20件。`q` は名前・説明文・経歴の部分一致（OR） | CP-4 |
| `GET /api/cosplayers/{id}/` | 全項目＋`sources` | CP-5 |

- `ReadOnlyModelViewSet` と `PageNumberPagination(page_size=20)`。フィルターは `django-filter` を使わず `get_queryset` で実装（パラメーターが少ないため依存を増やさない）。
- `select_related("venue")`・`prefetch_related("sources")` で N+1 を防ぐ。
- シリアライザーで `url`・`source_url`・`sns_links` のうち `http`/`https` 以外を除外（NF-5、表示側でも再確認）。

## フロントエンド（Next.js、output: "export"）

- `basePath`・`assetPrefix` は `/apps/cosplay-event-info`（固定値、NF-4）。API の URL は `NEXT_PUBLIC_API_BASE_URL`（既定 `http://localhost:8000`）。
- 静的出力のため詳細ページは動的ルートではなくクエリ（`/events/detail/?id=1`）で受ける。`useSearchParams` は `Suspense` で囲む。

| 画面 | パス | 内容 | 要件 |
|---|---|---|---|
| トップ | `/` | サイトの説明、今日以降のイベント5件、各画面への導線 | EV-7 |
| イベント一覧 | `/events/` | 検索フォーム（キーワード・期間・都道府県）→ 結果一覧・ページ送り。条件は URL のクエリに反映 | EV-7〜EV-10 |
| イベント詳細 | `/events/detail/?id=` | 全項目、取得元の一覧、「Google マップで開く」リンク | EV-11, MAP-3 |
| 地図 | `/map/` | 期間（既定: 今日〜30日後）→ 会場一覧（件数付き）→ 選んだ会場の Google マップ埋め込み（`https://www.google.com/maps?q=<会場名 住所>&output=embed`）とその会場のイベント | MAP-1, MAP-2 |
| コスプレイヤー一覧 | `/cosplayers/` | キーワード検索・ページ送り | CP-4 |
| コスプレイヤー詳細 | `/cosplayers/detail/?id=` | 名前・SNS・経歴・説明文・備考・取得元 | CP-5 |

- `src/lib/api.ts`（fetch の薄いラッパーと型）、`src/lib/url.ts`（`safeHttpUrl`・`googleMapsEmbedUrl`・`googleMapsSearchUrl`）、`src/lib/format.ts`（日付範囲の表示）。
- 文字列は React のテキストとして描画し、`dangerouslySetInnerHTML` は使わない（NF-5）。外部リンクは `rel="noopener noreferrer"`。

## 横断的関心事

- **セキュリティ・プライバシー**: API は読み取り専用で認証情報を持たない。`DJANGO_SECRET_KEY` は環境変数。`APP_ENV=production` で未設定なら `ImproperlyConfigured` で起動を中止（NF-3）、`DEBUG` は `APP_ENV=development` のときだけ有効。CORS は `CORS_ORIGINS` で指定したオリジンのみ。収集した URL は http/https のみ通す（`javascript:` 対策）。コスプレイヤーの情報は Wikipedia 等で公開されている範囲に限り、画像は保存しない。`ANTHROPIC_API_KEY` は環境変数のみで扱い、ログに出さない。
- **パフォーマンス**: 想定データは数千件規模で SQLite で十分。イベントの重複判定は開始日で候補を絞り、コスプレイヤーは名前の長さで絞る。一覧はページ送り（NF-2）。
- **オブザーバビリティ**: バッチは `logging` でサイトごとの件数・失敗 URL を出力し、取得結果はすべて `FetchedPage` に残る（Django 管理画面で確認可能）。
- **テスト戦略**: バックエンドは pytest-django。通信は `httpx.MockTransport`、AI は偽のクライアント、HTML は `tests/fixtures/` の固定データで、実サイト・実 API に接続しない。類似度・日付解析は境界値をテスト。フロントエンドは Vitest + Testing Library で `fetch` をモックし、検索フォーム・地図の URL 生成・安全な URL の判定をテスト。
- **ロールアウト**: 新規プロジェクトのため既存機能への影響なし。DB は Django のマイグレーションで作成。Docker イメージは起動時に `migrate` を実行してから gunicorn を起動する。ロールバックはコンテナとボリュームの削除で足りる。

## 検討した代替案

- **類似度に `rapidfuzz` / `python-Levenshtein` を使う**: 高速だが、件数が少なく自前実装で十分。アルゴリズムを示すポートフォリオの意図からも自前実装を採用。
- **Google Maps JavaScript API で複数マーカーを表示**: 一覧性は高いが API キーと課金設定が必須になり、デモを誰でも動かせなくなるため不採用。
- **Playwright 等のヘッドレスブラウザーで収集**: JS で描画するサイトにも対応できるが、依存と実行コストが大きいため不採用。静的 HTML と JSON-LD で取れる範囲に限定。
- **重複統合を収集後のバッチで一括実行**: 取り込み時に判定するほうが DB が常に重複のない状態に保てるため、取り込み時の判定を採用。
- **`django-filter` で検索条件を実装**: パラメーターが少なく依存を増やす利点が小さいため不採用。
- **AI の正規化を必須にする**: 正規化の品質は上がるが、API キーなしで動かせなくなるため任意機能とした。

## 要件との対応

| 要件 | 設計要素 |
|---|---|
| EV-1, EV-2 | parsers/events.py, fetch_events |
| EV-3, CP-3 | similarity.py, importer.py |
| EV-4〜EV-6 | normalizer.py |
| EV-7〜EV-11, NF-2 | `/api/events/`, イベント一覧・詳細画面 |
| MAP-1〜MAP-3 | `/api/venues/`, 地図画面, イベント詳細のリンク |
| CP-1, CP-2 | parsers/cosplayers.py, fetch_cosplayers |
| CP-4, CP-5 | `/api/cosplayers/`, コスプレイヤー一覧・詳細画面 |
| FT-1〜FT-4, NF-1 | fetcher.py, FetchedPage |
| NF-3 | config/settings.py |
| NF-4 | next.config.ts |
| NF-5 | シリアライザーの URL 除外, `safeHttpUrl` |
