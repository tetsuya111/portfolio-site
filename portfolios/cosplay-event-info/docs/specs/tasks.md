# コスプレイベント情報まとめサイト 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 複数サイトのコスプレイベント・コスプレイヤー情報を収集・重複統合し、検索と地図表示ができるサイトを作る。

**Architecture:** Django/DRF の読み取り専用 API と管理コマンド（バッチ）、Next.js の静的出力フロントエンド。収集は Fetcher → Parser → Normalizer → Importer の順に分け、それぞれを単体テストする。

**Tech Stack:** Python 3.12 / Django 5.2 / DRF / httpx / BeautifulSoup4 / pytest-django / ruff、Next.js 16 / React 19 / TypeScript / Vitest

**Spec:** [requirements.md](requirements.md)・[design.md](design.md)

## Global Constraints

- すべてのファイルは `portfolios/cosplay-event-info/` 配下に置く（作業ログはリポジトリルートの `logs/`）。
- 類似度のしきい値: イベント `0.85`（かつ開始日が同じ）、コスプレイヤー `0.9`。
- 一覧 API は1ページ20件。同じホストへのリクエスト間隔は1秒以上。
- `basePath` は `/apps/cosplay-event-info`（固定値）。
- テストは実サイト・実 API に接続しない。
- README・コメントは日本語。

## Review Focus

- 12月に「1/10(土)」と書かれた翌年1月のイベント → 翌年の日付として解釈する（Task 6 `test_parse_date_range_rolls_over_year`）。
- 元データで終了日が開始日より前・終了日なし → 終了日を開始日にそろえる（Task 6 `test_parse_date_range_single_day`・Task 8 `test_import_event_fixes_end_before_start`）。
- 検索の `from`/`to` に不正な日付 → 500 ではなく 400（Task 10 `test_events_invalid_date_returns_400`）。
- 元データの `javascript:` リンク → API にも画面にも出さない（Task 10 `test_unsafe_urls_are_removed`・Task 11 `safeHttpUrl` のテスト）。
- カテゴリーページの「次のページ」が同じページを指す → 無限ループしない（Task 9 `test_fetch_cosplayers_stops_on_visited_page`）。

---

### Task 1: バックエンドの土台（設定・ヘルスチェック・npm スクリプト）— NF-3

**Files:**
- Create: `backend/pyproject.toml`, `backend/manage.py`, `backend/config/{__init__,settings,urls,wsgi}.py`, `backend/catalog/{__init__,apps,views}.py`, `backend/conftest.py`, `scripts/run-backend.mjs`, `package.json`, `.gitignore`, `.env.example`
- Test: `backend/tests/test_health.py`, `backend/tests/test_settings.py`

**Interfaces:**
- Produces: `config.settings.build_secret_key(env: str, value: str | None) -> str`、`GET /api/health/`、設定値 `EVENT_SIMILARITY_THRESHOLD=0.85`・`COSPLAYER_SIMILARITY_THRESHOLD=0.9`・`FETCH_MIN_INTERVAL=1.0`

- [ ] `test_health_returns_ok`: `client.get("/api/health/").json() == {"status": "ok"}`
- [ ] `test_production_without_secret_raises`: `build_secret_key("production", None)` が `ImproperlyConfigured`。`test_development_uses_dev_key`: `build_secret_key("development", None)` が空でない文字列。
- [ ] 実装（`DATABASE_PATH` 環境変数で SQLite の場所、`CORS_ORIGINS` はカンマ区切り、`DEBUG` は `APP_ENV=development` のみ）→ `npm run test:backend` 成功 → `npm run lint:backend` 成功 → コミット

### Task 2: モデルとマイグレーション・管理画面 — FT-1, EV-1, CP-1

**Files:** Create `backend/catalog/models.py`, `backend/catalog/admin.py`, `backend/catalog/migrations/0001_initial.py`（makemigrations で生成）／Test `backend/tests/test_models.py`

**Interfaces:**
- Produces: `FetchedPage(url, kind, status_code, content, error, fetched_at)` と `FetchedPage.is_success: bool`、`Venue(name, prefecture, address)`、`Event(name, url, location_raw, venue, start_date, end_date, notes, source_url, sources)`、`Cosplayer(name, sns_links, career, description, notes, source_url, sources)`

- [ ] `test_event_end_before_start_violates_constraint`（`IntegrityError`）、`test_fetched_page_url_unique`、`test_fetched_page_is_success`（200→True、404・None→False）
- [ ] 実装 → テスト成功 → `python manage.py makemigrations --check` で差分なし → コミット

### Task 3: 名前の類似度 — EV-3, CP-3

**Files:** Create `backend/catalog/collector/{__init__,similarity}.py`／Test `backend/tests/test_similarity.py`

**Interfaces:** Produces `levenshtein(a: str, b: str) -> int`、`normalize_name(s: str) -> str`、`similarity(a: str, b: str) -> float`

- [ ] テスト: `levenshtein("kitten","sitting") == 3`、`levenshtein("", "abc") == 3`、`normalize_name("Ｃｏｓ Fes！") == normalize_name("cosfes")`、`similarity("a","a") == 1.0`、`similarity("", "") == 0.0`、`similarity("コスプレ博 in TFT", "コスプレ博inTFT") == 1.0`
- [ ] 実装 → 成功 → コミット

### Task 4: 開催場所の正規化 — EV-4〜EV-6

**Files:** Create `backend/catalog/collector/normalizer.py`／Test `backend/tests/test_normalizer.py`

**Interfaces:** Produces `NormalizedLocation(venue_name: str, prefecture: str, address: str)`（dataclass）、`RuleBasedNormalizer().normalize(raw: str) -> NormalizedLocation`、`ClaudeNormalizer(api_key: str, client: httpx.Client, fallback: RuleBasedNormalizer)`、`get_normalizer(env: Mapping[str, str] | None = None)`、`PREFECTURES: tuple[str, ...]`（47件）

- [ ] テスト: `"東京ビッグサイト 西1ホール"` → 会場名 `東京ビッグサイト`・`東京都`、`"ビッグサイト"`（別名）→ 同じ、`"大阪府大阪市 某ホール"` → 都道府県 `大阪府`、空文字 → 会場名 `""`。Claude: MockTransport の正常 JSON を採用、壊れた JSON・不正な都道府県・500 はルールベースの結果。`get_normalizer({})` は RuleBased、`{"ANTHROPIC_API_KEY": "x"}` は Claude。
- [ ] 実装（Claude API は `POST https://api.anthropic.com/v1/messages`、ヘッダー `x-api-key`・`anthropic-version: 2023-06-01`、モデル `claude-haiku-5-5`）→ 成功 → コミット

### Task 5: ページ取得（Fetcher）— FT-1〜FT-4, NF-1

**Files:** Create `backend/catalog/collector/fetcher.py`／Test `backend/tests/test_fetcher.py`

**Interfaces:** Consumes `FetchedPage`。Produces `Fetcher(client: httpx.Client, *, min_interval: float = 1.0, sleep=time.sleep, clock=time.monotonic)`、`Fetcher.fetch(url: str, kind: str, *, force: bool = False) -> FetchedPage | None`

- [ ] テスト: 成功時に `FetchedPage` が保存される／取得済み URL は通信しない（MockTransport の呼び出し回数）／`force=True` で再取得／404 は `error` 付きで保存され `None`／通信例外も同様／robots.txt の `Disallow` は取得しない／同じホストへの連続取得で `sleep` が呼ばれる（合計待ち時間 ≥ 間隔）
- [ ] 実装 → 成功 → コミット

### Task 6: イベントの抽出 — EV-1

**Files:** Create `backend/catalog/collector/parsers/{__init__,dates,events}.py`, `backend/tests/fixtures/events_jsonld.html`, `backend/tests/fixtures/events_list.html`／Test `backend/tests/test_parse_events.py`

**Interfaces:** Produces `parse_date_range(text: str, today: date) -> tuple[date, date] | None`、`EventItem(name, url, location, start_date, end_date, notes)`、`SiteConfig(name, start_urls, item, name_sel, link, date, location, notes)`、`SITES: dict[str, SiteConfig]`、`parse_events(html: str, base_url: str, config: SiteConfig, today: date) -> list[EventItem]`

- [ ] テスト: `"2026年12月5日"`、`"2026/12/5〜2026/12/6"`、`"12/5(土)〜12/6(日)"`（today=2026-11-19 → 2026年）、`test_parse_date_range_rolls_over_year`（today=2026-12-20, `"1/10(土)"` → 2027-01-10）、`test_parse_date_range_single_day`（終了日＝開始日）、日付なし → None。JSON-LD の固定データから2件、`@graph` 形式も抽出。セレクターの固定データからリンクを絶対 URL にして抽出。名前・日付のない項目は捨てる。
- [ ] 実装 → 成功 → コミット

### Task 7: コスプレイヤーの抽出 — CP-1

**Files:** Create `backend/catalog/collector/parsers/cosplayers.py`, `backend/tests/fixtures/wiki_category.html`, `backend/tests/fixtures/wiki_person.html`／Test `backend/tests/test_parse_cosplayers.py`

**Interfaces:** Produces `CosplayerItem(name, sns_links: list[str], career, description, notes)`、`parse_category_page(html: str, base_url: str) -> tuple[list[str], str | None]`、`parse_person_page(html: str, url: str) -> CosplayerItem`、`WIKIPEDIA_CATEGORY_URL`

- [ ] テスト: カテゴリーから人物 URL（絶対 URL）と次ページ URL、次ページがなければ None。人物ページから名前・説明文（脚注 `[1]` 除去）・経歴（新形式 `div.mw-heading` の見出し）・SNS（x.com と instagram のみ、Wikipedia 内リンクは除外、重複なし）。
- [ ] 実装 → 成功 → コミット

### Task 8: 取り込みと重複統合 — EV-3, EV-4, CP-3

**Files:** Create `backend/catalog/collector/importer.py`／Test `backend/tests/test_importer.py`

**Interfaces:** Consumes Task 3・4・6・7。Produces `import_event(item: EventItem, page: FetchedPage, normalizer) -> tuple[Event, bool]`（bool は新規作成なら True）、`import_cosplayer(item: CosplayerItem, page: FetchedPage) -> tuple[Cosplayer, bool]`

- [ ] テスト: 類似名・同じ開始日は統合され `sources` が2件／類似名でも開始日が違えば別／空の備考を補う／`test_import_event_fixes_end_before_start`／同じ `location_raw` は2回目に正規化を呼ばない（呼び出し回数）・同じ `Venue` を共有／コスプレイヤーは類似度0.9以上で統合し SNS を重複なく追加、0.9未満は別人
- [ ] 実装 → 成功 → コミット

### Task 9: バッチ（管理コマンド）— EV-2, CP-2, FT-2〜FT-4

**Files:** Create `backend/catalog/management/__init__.py`, `backend/catalog/management/commands/{__init__,fetch_events,fetch_cosplayers,seed_demo}.py`, `backend/catalog/collector/runner.py`／Test `backend/tests/test_commands.py`

**Interfaces:** Produces `run_event_collection(fetcher: Fetcher, sites: Iterable[SiteConfig], normalizer, today: date, force: bool) -> dict[str, dict[str, int]]`、`run_cosplayer_collection(fetcher: Fetcher, start_url: str, limit: int | None, force: bool) -> dict[str, int]`。コマンドは `--site`・`--force`・`--limit`

- [ ] テスト: MockTransport で1サイト実行 → イベント2件、2回目は取得スキップで件数が増えない／`--site` 指定外は取得しない／取得失敗サイトがあっても他サイトを処理／`test_fetch_cosplayers_stops_on_visited_page`／`--limit 1` で1人だけ／`seed_demo` を2回実行しても件数が同じ
- [ ] 実装 → 成功 → コミット

### Task 10: API — EV-7〜EV-11, MAP-1, CP-4, CP-5, NF-2, NF-5

**Files:** Create `backend/catalog/{serializers,api,urls}.py`、Modify `backend/config/urls.py`／Test `backend/tests/test_api_events.py`, `backend/tests/test_api_cosplayers.py`

**Interfaces:** Produces design.md の API 表のとおり（レスポンス: 一覧は `{count, next, previous, results}`）。Event の JSON: `{id, name, url, location_raw, venue: {id,name,prefecture,address}|null, start_date, end_date, notes, source_url}`、詳細は＋`sources: [{url, fetched_at}]`。Venue: `{id, name, prefecture, address, event_count, events: [{id, name, start_date, end_date}]}`。Cosplayer: `{id, name, sns_links, career, description, notes, source_url}`＋詳細で `sources`

- [ ] テスト: 開始日昇順／`q` が会場名・備考にも当たる／期間の重なり（期間の前後にはみ出すイベントも含む）／`prefecture`／`test_events_invalid_date_returns_400`／21件で2ページ目に1件／詳細に `sources`／`/api/venues/` の件数と期間外の除外／コスプレイヤーの検索・詳細／`test_unsafe_urls_are_removed`
- [ ] 実装 → 成功 → コミット

### Task 11: フロントエンドの土台と共通ライブラリ — NF-4, NF-5, MAP-2, MAP-3

**Files:** Create `frontend/{package.json,next.config.ts,tsconfig.json,eslint.config.mjs,vitest.config.ts,vitest.setup.ts,scripts/run-vitest.mjs}`, `frontend/src/app/{layout.tsx,globals.css,page.tsx}`, `frontend/src/lib/{api,url,format,types}.ts`, `frontend/src/components/SiteHeader.tsx`／Test `frontend/src/lib/{api,url,format}.test.ts`

**Interfaces:** Produces `safeHttpUrl(u: string | null | undefined): string | null`、`googleMapsEmbedUrl(query: string): string`、`googleMapsSearchUrl(query: string): string`、`formatDateRange(start: string, end: string): string`、`fetchEvents(params: EventQuery): Promise<Page<EventSummary>>`、`fetchEvent(id: number)`、`fetchVenues(from: string, to: string)`、`fetchCosplayers(params)`、`fetchCosplayer(id)`、`ApiError`

- [ ] テスト: `safeHttpUrl("javascript:alert(1)") === null`・`https` はそのまま／埋め込み URL に `output=embed` と URL エンコードされた検索語／`formatDateRange("2026-12-05","2026-12-05") === "2026/12/05"`、異なれば `"2026/12/05 〜 2026/12/06"`／`fetchEvents` が空の条件をクエリに含めない・エラー時に `ApiError`
- [ ] 実装 → `npm --prefix frontend test`・`lint`・`build` 成功 → コミット

### Task 12: イベント画面（トップ・一覧・詳細）— EV-7〜EV-11, MAP-3

**Files:** Create `frontend/src/app/events/page.tsx`, `frontend/src/app/events/detail/page.tsx`, `frontend/src/components/{EventSearchForm,EventList,Pagination}.tsx`、Modify `frontend/src/app/page.tsx`／Test `frontend/src/components/{EventSearchForm,EventList}.test.tsx`

- [ ] テスト: フォーム送信で入力値（キーワード・期間・都道府県）が `onSearch` に渡る／一覧に会場名・日付・詳細へのリンク、0件で「該当するイベントはありません」
- [ ] 実装 → テスト・lint・build 成功 → コミット

### Task 13: 地図・コスプレイヤー画面 — MAP-1, MAP-2, CP-4, CP-5

**Files:** Create `frontend/src/app/map/page.tsx`, `frontend/src/app/cosplayers/page.tsx`, `frontend/src/app/cosplayers/detail/page.tsx`, `frontend/src/components/{VenueMap,CosplayerList,CosplayerProfile}.tsx`／Test `frontend/src/components/{VenueMap,CosplayerProfile}.test.tsx`

- [ ] テスト: 会場一覧の件数表示・選択で iframe の `src` が選んだ会場の埋め込み URL になる／プロフィールで SNS は安全な URL だけリンクになる・経歴と説明文がテキストで表示される（HTML タグがそのまま文字として出る）
- [ ] 実装 → テスト・lint・build 成功 → コミット

### Task 14: Docker・README・索引

**Files:** Create `backend/Dockerfile`, `docker-compose.yml`, `README.md`、Modify `docs/projects.md`（リポジトリルート）

- [ ] README に機能・構成・セットアップ・バッチの使い方（`--site`・`--force`・`ANTHROPIC_API_KEY`）・対象サイトのセレクター調整方法・注意（利用規約と robots.txt の確認）を日本語で書く
- [ ] ルートの `npm test`・`npm run lint`・`npm run build` 成功 → コミット
