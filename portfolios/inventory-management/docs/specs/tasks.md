# 在庫管理システム Implementation Plan（tasks.md）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FastAPI + Next.js の在庫管理システム（認証・ユーザー・商品 CRUD・入出庫・履歴・集計・ダッシュボード）を `portfolios/inventory-management/` に作る。

**Architecture:** FastAPI の REST API（SQLAlchemy 2.0 + Alembic + SQLite）と、静的出力の Next.js SPA。在庫の増減は条件付き UPDATE と記録の INSERT を1トランザクションで行う。

**Tech Stack:** Python 3.12・FastAPI・SQLAlchemy 2・Alembic・pydantic-settings・PyJWT・bcrypt・pytest・ruff／Node 24・Next.js 15・React 19・TypeScript・Vitest・Testing Library・ESLint

**Spec:** [requirements.md](requirements.md)・[design.md](design.md)

以下、パスは `portfolios/inventory-management/` からの相対パス。バックエンドのコマンドは `backend/` で、venv（`backend/.venv`）の python を使う。

## Global Constraints

- `portfolios/inventory-management/` の外のファイルを変更しない。作業ログは `logs/<yyyymmdd_hhMMss>_<種別>_<内容>.md`（プロジェクト内）に書く。
- README・ドキュメント・コメントは日本語。
- `.env`・DB ファイル・`.venv`・`node_modules`・`.next`・`out` はコミットしない（`.gitignore`）。
- 権限区分は `admin` / `staff`。数量は 1〜1,000,000 の整数。履歴の limit は 1〜100（既定20）。トークン有効期限は既定60分。本番の JWT_SECRET は32文字以上。
- エラーコード: 認証なし・不正 401、権限なし 403、なし・削除済み 404、重複・在庫不足 409、入力不正 422。

## Review Focus

- 削除済みの商品に入出庫しようとする → 404（Task 6 でテスト）
- 削除済みの商品の商品コードで新規登録する → 409（Task 5 でテスト）
- 無効化されたユーザーの有効なトークンで API を呼ぶ → 401（Task 3 でテスト）
- 数量に `1.5`・`"3"`・`0`・`1000001` を送る → 422（Task 6 でテスト）
- 履歴の `date_to` に当日を指定したとき、当日の記録が含まれる（両端を含む）（Task 7 でテスト）

---

### Task 1: バックエンドの雛形・設定・テスト基盤（NFR-ENV-1・NFR-SEC-2・3・NFR-QA-2）

**Files:**
- Create: `backend/pyproject.toml`、`backend/app/__init__.py`、`backend/app/config.py`、`backend/app/db.py`、`backend/app/main.py`、`backend/tests/conftest.py`、`backend/tests/test_health.py`、`backend/tests/test_config.py`、`package.json`、`scripts/run-backend.mjs`、`.gitignore`、`.env.example`

**Interfaces:**
- Produces: `Settings`（`app_env, database_url, jwt_secret, access_token_expire_minutes, cors_origins: list[str]`）、`get_settings()`、`Settings.validate_for_env()`（production で秘密鍵が不正なら `ValueError`）、`create_app(settings: Settings | None = None) -> FastAPI`、`Base`（DeclarativeBase）、`get_db()`（Session を yield）、`make_engine(url)`（SQLite なら `check_same_thread=False`・`busy_timeout=5000`・外部キー有効）。conftest の `client`（一時 SQLite で `create_all` 済み・`get_db` を差し替えた TestClient）と `db_session`。

- [ ] Step 1: `test_health_returns_ok`（`GET /health` → 200 `{"status":"ok"}`）、`test_production_requires_strong_secret`（`APP_ENV=production` かつ秘密鍵31文字 → `ValueError`、32文字 → OK）、`test_cors_origins_parsed_from_comma_string` を書く。
- [ ] Step 2: venv を作り依存を入れ、`python -m pytest` で失敗を確認する。
- [ ] Step 3: 上記の Interfaces を実装する。ルートの `package.json` に `test`（backend の pytest → frontend の vitest）、`lint`（ruff check → frontend の eslint・tsc）、`build`（frontend の next build）を置き、`scripts/run-backend.mjs` で OS に応じた venv の python を選ぶ。
- [ ] Step 4: `python -m pytest`・`python -m ruff check .` が成功することを確認する。
- [ ] Step 5: コミットする。

### Task 2: モデルと初期マイグレーション（REQ-PRD・INV・USR のデータ、NFR-ENV-2）

**Files:**
- Create: `backend/app/models.py`、`backend/alembic.ini`、`backend/alembic/env.py`、`backend/alembic/script.py.mako`、`backend/alembic/versions/0001_initial.py`、`backend/tests/test_models.py`、`backend/tests/test_migrations.py`

**Interfaces:**
- Produces: `User`、`Product`、`StockMovement`（列・制約は design.md の表のとおり。`created_at`／`updated_at` は UTC の `DateTime(timezone=True)`）、`utcnow()`。

- [ ] Step 1: `test_stock_cannot_be_negative`（`stock=-1` で commit → `IntegrityError`）、`test_sku_unique`、`test_migration_creates_tables`（一時 DB に `alembic upgrade head` → 3テーブルが存在、`downgrade base` → 消える）を書く。
- [ ] Step 2: 失敗を確認する。
- [ ] Step 3: モデルとマイグレーションを実装する。`alembic/env.py` は `get_settings().database_url`（`-x db_url=` で上書き可）を使う。
- [ ] Step 4: テスト成功を確認する。
- [ ] Step 5: コミットする。

### Task 3: パスワード・JWT・ログイン・/users/me（REQ-AUTH-1〜6、USR-7、NFR-SEC-1）

**Files:**
- Create: `backend/app/security.py`、`backend/app/deps.py`、`backend/app/schemas.py`、`backend/app/routers/__init__.py`、`backend/app/routers/auth.py`、`backend/app/routers/users.py`、`backend/tests/test_auth.py`、`backend/tests/factories.py`
- Modify: `backend/app/main.py`（ルーター登録）

**Interfaces:**
- Produces: `hash_password(p) -> str`、`verify_password(p, h) -> bool`、`create_access_token(user: User, settings) -> str`、`decode_token(token, settings) -> dict`（不正なら `jwt.PyJWTError`）、`get_current_user`、`require_admin`、`authenticate(db, username, password) -> User | None`、スキーマ `UserOut`・`Token`。`tests/factories.py` の `create_user(db, username="alice", password="password123", role="staff", is_active=True) -> User` と `auth_headers(client, username, password) -> dict`。

- [ ] Step 1: `test_login_success_returns_token`、`test_login_wrong_password_401`・`test_login_unknown_user_401`（両者の `detail` が同じ）、`test_login_inactive_user_401`、`test_me_returns_user_without_password`、`test_me_without_token_401`、`test_me_with_expired_token_401`、`test_me_with_bad_signature_401`、`test_token_of_deactivated_user_401`、`test_password_is_hashed` を書く。
- [ ] Step 2: 失敗を確認する。
- [ ] Step 3: 実装する（存在しないユーザーにもダミーハッシュで照合）。
- [ ] Step 4: テスト成功を確認する。
- [ ] Step 5: コミットする。

### Task 4: ユーザー登録・一覧・CLI（REQ-USR-1〜6）

**Files:**
- Create: `backend/app/cli.py`、`backend/tests/test_users.py`、`backend/tests/test_cli.py`
- Modify: `backend/app/routers/auth.py`（register）、`backend/app/routers/users.py`（一覧）、`backend/app/schemas.py`（`UserCreate`）

**Interfaces:**
- Produces: `POST /auth/register`（admin）、`GET /users`（admin、ID 順）、`UserCreate(username, password, role="staff")`、CLI `python -m app.cli create-admin --username U --password P`（既存なら終了コード1）・`python -m app.cli seed-demo`（デモ用の admin／staff と商品・入出庫を作る。既にあれば何もしない）。

- [ ] Step 1: `test_admin_can_register_user_and_user_can_login`、`test_staff_cannot_register_403`、`test_duplicate_username_409`、`test_invalid_username_422`（`ab`・`a b`）、`test_short_password_422`、`test_list_users_admin_only`、`test_cli_create_admin`、`test_cli_create_admin_duplicate_exits_1`、`test_cli_seed_demo_idempotent` を書く。
- [ ] Step 2: 失敗を確認する。
- [ ] Step 3: 実装する。
- [ ] Step 4: テスト成功を確認する。
- [ ] Step 5: コミットする。

### Task 5: 商品マスタ CRUD（REQ-PRD-1〜10）

**Files:**
- Create: `backend/app/routers/products.py`、`backend/tests/test_products.py`
- Modify: `backend/app/schemas.py`（`ProductIn`・`ProductOut`）、`backend/app/main.py`

**Interfaces:**
- Produces: `ProductIn(sku, name, category=None, unit="個", unit_price=None, reorder_point=0, description=None)`、`ProductOut`、`get_active_product(db, id) -> Product`（なし・削除済みで 404）、`create_product(db, sku=..., name=..., **kw)`（`tests/factories.py` に追加）。

- [ ] Step 1: `test_create_product_stock_zero`、`test_create_duplicate_sku_409`、`test_create_with_deleted_sku_409`、`test_create_invalid_422`（name 欠落・sku 51文字・unit_price -1）、`test_list_sorted_by_sku_excludes_deleted`、`test_list_search_q`（sku・name の部分一致）、`test_get_detail`・`test_get_missing_404`、`test_update_ignores_stock`、`test_update_duplicate_sku_409`、`test_admin_delete_then_404`、`test_staff_delete_403`、`test_products_require_auth_401` を書く。
- [ ] Step 2: 失敗を確認する。
- [ ] Step 3: 実装する。
- [ ] Step 4: テスト成功を確認する。
- [ ] Step 5: コミットする。

### Task 6: 入出庫の記録（REQ-INV-1〜7、SUM-2）

**Files:**
- Create: `backend/app/services/__init__.py`、`backend/app/services/inventory.py`、`backend/app/routers/inventory.py`、`backend/tests/test_inventory_movements.py`、`backend/tests/test_inventory_concurrency.py`
- Modify: `backend/app/schemas.py`（`MovementCreate`・`MovementOut`）、`backend/app/main.py`

**Interfaces:**
- Produces: `record_movement(db, *, user, product_id, movement_type: Literal["in","out"], quantity, note) -> StockMovement`、例外 `ProductNotFound`・`InsufficientStock`、`movement_to_out(m) -> MovementOut`。

- [ ] Step 1: `test_in_increases_stock`、`test_out_decreases_stock`、`test_out_exceeding_stock_409_and_unchanged`（記録数も変わらない）、`test_quantity_invalid_422`（0・-1・1.5・"3"・1000001）、`test_movement_on_deleted_product_404`、`test_movement_on_missing_product_404`、`test_movement_records_user_and_stock_after`、`test_concurrent_outs_never_negative`（ファイルの SQLite、在庫10に対し8スレッドが各3出庫 → 成功は3件、最終在庫1、合計の一致）を書く。
- [ ] Step 2: 失敗を確認する。
- [ ] Step 3: design.md「在庫の増減と整合性」の手順で実装する。在庫不足は WARNING ログを出す。
- [ ] Step 4: テスト成功を確認する。
- [ ] Step 5: コミットする。

### Task 7: 入出庫履歴（REQ-HIS-1〜4）

**Files:**
- Create: `backend/tests/test_inventory_history.py`
- Modify: `backend/app/services/inventory.py`（`list_history`）、`backend/app/routers/inventory.py`、`backend/app/schemas.py`（`HistoryPage`）

**Interfaces:**
- Produces: `list_history(db, *, product_id=None, movement_type=None, date_from: date | None, date_to: date | None, limit=20, offset=0) -> tuple[list[StockMovement], int]`、`HistoryPage(items, total, limit, offset)`。

- [ ] Step 1: `test_history_newest_first_with_names`、`test_history_filter_product_and_type`、`test_history_filter_date_range_inclusive`（`created_at` を直接設定した記録で、`date_to` 当日の記録を含む）、`test_history_pagination_total`、`test_history_limit_over_100_422`、`test_history_includes_deleted_product` を書く。
- [ ] Step 2: 失敗を確認する。
- [ ] Step 3: 実装する（`date_to` は翌日0時未満で比較）。
- [ ] Step 4: テスト成功を確認する。
- [ ] Step 5: コミットする。

### Task 8: 在庫集計（REQ-SUM-1〜4）

**Files:**
- Create: `backend/tests/test_inventory_summary.py`
- Modify: `backend/app/services/inventory.py`（`get_summary`）、`backend/app/routers/inventory.py`、`backend/app/schemas.py`（`SummaryItem`・`Summary`）

**Interfaces:**
- Produces: `get_summary(db) -> Summary`（`items: list[SummaryItem]`、`total_products`、`total_stock`、`low_stock_count`）。

- [ ] Step 1: `test_summary_empty`（すべて0・items 空）、`test_summary_counts_and_low_flag`（stock == reorder_point で is_low）、`test_summary_excludes_deleted`、`test_summary_matches_movement_totals`（ランダムな入出庫50件のあと、各商品で stock == Σin − Σout）を書く。
- [ ] Step 2: 失敗を確認する。
- [ ] Step 3: 実装する。
- [ ] Step 4: テスト成功を確認する。
- [ ] Step 5: コミットする。

### Task 9: フロントエンドの雛形・API クライアント・認証・ログイン画面（REQ-AUTH-7・8、NFR-ENV-4）

**Files:**
- Create: `frontend/package.json`、`frontend/tsconfig.json`、`frontend/next.config.ts`、`frontend/eslint.config.mjs`、`frontend/vitest.config.ts`、`frontend/vitest.setup.ts`、`frontend/src/lib/types.ts`、`frontend/src/lib/api.ts`、`frontend/src/lib/auth.tsx`、`frontend/src/components/AppShell.tsx`、`frontend/src/app/layout.tsx`、`frontend/src/app/globals.css`、`frontend/src/app/login/page.tsx`、`frontend/src/app/page.tsx`（仮）、`frontend/src/lib/api.test.ts`、`frontend/src/lib/auth.test.tsx`

**Interfaces:**
- Produces: `ApiError(status, message)`、`apiFetch<T>(path, init?) -> Promise<T>`（Bearer 付与、204 は `undefined`、エラー時 `detail` を message に、401 で `onUnauthorized` を呼ぶ）、`login(username, password)`、`getToken()/setToken()/clearToken()`、`AuthProvider`・`useAuth() -> {user, loading, signIn, signOut}`、`RequireAuth`（未ログインなら `/login` へ）、`AppShell`（ナビ。`/users` は admin のみ表示）、`types.ts` の `User`・`Product`・`Movement`・`HistoryPage`・`Summary`。

- [ ] Step 1: `apiFetch attaches bearer token`、`apiFetch throws ApiError with detail`、`apiFetch calls onUnauthorized on 401`、`login posts form-encoded body`、`signOut clears token`、`RequireAuth redirects when no token` を書く。
- [ ] Step 2: `npm install` 後、`npm test` で失敗を確認する。
- [ ] Step 3: 実装する（`output: "export"`、`basePath`・`assetPrefix` は `NEXT_PUBLIC_BASE_PATH`、`trailingSlash: true`、`images.unoptimized`）。
- [ ] Step 4: `npm test`・`npm run lint`・`npm run build` が成功することを確認する。
- [ ] Step 5: コミットする。

### Task 10: 商品画面（REQ-PRD の画面）

**Files:**
- Create: `frontend/src/components/ProductForm.tsx`、`frontend/src/components/ProductForm.test.tsx`、`frontend/src/app/products/page.tsx`、`frontend/src/app/products/new/page.tsx`、`frontend/src/app/products/edit/page.tsx`

**Interfaces:**
- Produces: `ProductForm({initial?, onSubmit(values: ProductInput) => Promise<void>, submitLabel})`（API のエラーを表示）、`ProductInput` 型。

- [ ] Step 1: `ProductForm requires sku and name`、`ProductForm submits numbers or null`、`ProductForm shows api error` を書く。
- [ ] Step 2: 失敗を確認する。
- [ ] Step 3: 一覧（検索・削除は admin のみ表示・確認ダイアログ）、登録、編集（`?id=`、`useSearchParams` を `Suspense` で包む）を実装する。
- [ ] Step 4: test・lint・build 成功を確認する。
- [ ] Step 5: コミットする。

### Task 11: 在庫一覧・入出庫登録・履歴画面（REQ-INV・HIS・SUM-5 の画面）

**Files:**
- Create: `frontend/src/lib/format.ts`、`frontend/src/lib/format.test.ts`、`frontend/src/lib/sort.ts`、`frontend/src/lib/sort.test.ts`、`frontend/src/app/inventory/page.tsx`、`frontend/src/app/inventory/record/page.tsx`、`frontend/src/app/inventory/history/page.tsx`

**Interfaces:**
- Produces: `formatDateTime(iso) -> string`、`formatNumber(n) -> string`、`movementTypeLabel(type) -> "入庫" | "出庫"`、`sortSummaryItems(items, order: "asc" | "desc") -> SummaryItem[]`（元の配列を変えない）。

- [ ] Step 1: `formatNumber adds separators`、`movementTypeLabel`、`sortSummaryItems by stock asc/desc without mutation` を書く。
- [ ] Step 2: 失敗を確認する。
- [ ] Step 3: 3画面を実装する（入出庫登録は商品の選択・数量・備考・区分、成功で登録後の在庫数を表示。履歴は絞り込みとページ送り）。
- [ ] Step 4: test・lint・build 成功を確認する。
- [ ] Step 5: コミットする。

### Task 12: ダッシュボード・ユーザー管理画面（REQ-DSH-1〜6、USR-1・5 の画面）

**Files:**
- Create: `frontend/src/components/BarChart.tsx`、`frontend/src/components/BarChart.test.tsx`、`frontend/src/lib/dashboard.ts`、`frontend/src/lib/dashboard.test.ts`、`frontend/src/app/users/page.tsx`
- Modify: `frontend/src/app/page.tsx`

**Interfaces:**
- Produces: `BarChart({data: {label, value}[], emptyText})`（最大値に対する割合の幅、0件なら emptyText）、`topStocked(items, n=10)`、`lowStockItems(items)`。

- [ ] Step 1: `BarChart renders bars proportional to max`、`BarChart shows empty text`、`topStocked returns top n by stock`、`lowStockItems filters is_low` を書く。
- [ ] Step 2: 失敗を確認する。
- [ ] Step 3: ダッシュボード（集計カード・上位10の棒グラフ・在庫が少ない商品・直近5件）とユーザー画面（一覧・登録フォーム、admin 以外は「権限がありません」）を実装する。
- [ ] Step 4: test・lint・build 成功を確認する。
- [ ] Step 5: コミットする。

### Task 13: Docker・開発環境・ドキュメント（NFR-ENV-1・3、NFR-DOC-1・2）

**Files:**
- Create: `backend/Dockerfile`、`backend/.dockerignore`、`docker-compose.yml`、`README.md`、`docs/architecture.md`、`backend/tests/test_docs.py`

**Interfaces:**
- Consumes: Task 1〜12 のすべて。

- [ ] Step 1: `test_openapi_lists_all_endpoints`（design.md の API 表の12＋`GET /users`＋`/health` がすべて OpenAPI に載る）を書く。
- [ ] Step 2: 失敗すれば修正し、成功を確認する。
- [ ] Step 3: Dockerfile（python:3.12-slim、非 root、CMD で `alembic upgrade head` → uvicorn。Windows でのチェックアウト時に CRLF で壊れないよう、シェルスクリプトのファイルは使わない）、docker-compose.yml（backend、名前付きボリュームを `/data` に、`DATABASE_URL=sqlite:////data/inventory.db`）、README（構成・起動・テスト・デモアカウント・環境変数・API 一覧・設計資料へのリンク）、architecture.md（構成図・ER 図・在庫整合性の説明・画面一覧）を書く。
- [ ] Step 4: `npm test`・`npm run lint`・`npm run build` 成功を確認する。
- [ ] Step 5: コミットする。
