# Billboard → Spotify Playlist 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Billboard Hot 100 のチャートURLから Spotify の非公開プレイリストを作るローカル Web アプリを作る。

**Architecture:** FastAPI バックエンド（スクレイピングバッチ・SQLite・Spotify OAuth/API）と Next.js フロントエンド。フロントは rewrites で `/api`・`/auth` をバックエンドへ転送し同一オリジンで動く。

**Tech Stack:** Python 3.12 / FastAPI / httpx / BeautifulSoup4 / sqlite3 / pytest / ruff、Node 24 / Next.js / React / TypeScript / vitest / Testing Library

**Spec:** [requirements.md](requirements.md)、[design.md](design.md)

## Global Constraints

- すべてのファイルは `portfolios/spotify-billboard-playlist/` 配下（作業ログのみルートの `logs/`）。
- 取得先ホストは `billboard.mryogaku.com` 固定、取得は HTTPS、リダイレクト非追従、タイムアウト 10 秒、応答上限 2 MB。
- Spotify スコープは `playlist-modify-private` のみ。作成は `POST /v1/me/playlists`、追加は `POST /v1/playlists/{id}/items`（100件ずつ）。
- 429 は `Retry-After`（上限30秒）に従い最大3回再試行。
- トークン・クライアントシークレットをブラウザへ返さない。ログにも出さない。
- 入力制約: `url` ≤ 2048 文字、`tracks` 1〜100件、`name` 1〜100文字、`title`/`artist` ≤ 200 文字。
- 既定値: `FRONTEND_URL=http://127.0.0.1:3000`、`SPOTIFY_REDIRECT_URI=http://127.0.0.1:3000/auth/callback`、`BACKEND_URL=http://127.0.0.1:8000`、`DB_PATH=backend/data/app.db`。

## Review Focus

1. アーティスト欄に `<a>` とプレーンテキストが混在・`&amp;` を含む行 → 連結・アンエスケープされた1つの文字列になる（Task 2 `test_parse_mixed_artist_markup`）。
2. `https://billboard.mryogaku.com.evil.example/` や `https://user@billboard.mryogaku.com/` のような紛らわしいURL → 不正として拒否（Task 1 `test_rejects_lookalike_hosts`）。
3. トップページ内の `dispHot100` リンクが相対パス（`/php/dispHot100.php?date=…`）→ 絶対URLに解決してから検証（Task 2 `test_find_latest_hot100_url_relative`）。
4. Spotify 検索で1曲もヒットしない曲が混ざる → その曲だけ `not_found` に入り、残りはチャート順で追加（Task 5 `test_build_playlist_skips_not_found_keeps_order`）。
5. アクセストークン期限切れ後の作成要求 → リフレッシュしてから成功（Task 5 `test_refreshes_expired_token`）。

---

### Task 1: バックエンドの土台と URL 検証（R2〜R4, N2）

**Files:**
- Create: `portfolios/spotify-billboard-playlist/package.json`, `scripts/run-python.mjs`, `.gitignore`
- Create: `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/batch/__init__.py`, `backend/app/batch/urls.py`
- Test: `backend/tests/test_urls.py`

**Interfaces:**
- Produces: `class InvalidChartUrl(ValueError)`, `@dataclass(frozen=True) class ChartTarget: kind: Literal["top","hot100"]; url: str`, `resolve_chart_url(url: str) -> ChartTarget`、定数 `HOST = "billboard.mryogaku.com"`, `TOP_URL = "https://billboard.mryogaku.com/"`
- Produces: ルート `package.json` scripts `test`（backend pytest → frontend vitest）、`lint`（ruff → frontend lint）、`build`（frontend build）、`setup`。`run-python.mjs` は `backend/.venv` の python を `cwd=backend` で起動する。

- [ ] Step 1: venv 作成と依存インストール（`py -3.12 -m venv backend/.venv`、`pip install -e backend[dev]`）
- [ ] Step 2: テストを書く: `test_top_page_variants`（`/`, `/#google_vignette`, `/index.php`, `/s/` → kind=top, url=TOP_URL）、`test_chart_php_normalized`（`/php/chart.php?date=2025-11-15` と `/s/php/chart.php?date=…` と `http://` → `https://billboard.mryogaku.com/php/dispHot100.php?date=2025-11-15`）、`test_rejects_bad_date`（`date=2025-1-5`, `date=x`, date なし）、`test_rejects_lookalike_hosts`（別ホスト・`.evil.example` 後置・userinfo・ポート指定・`ftp://`）
- [ ] Step 3: 失敗を確認 `npm run test:backend`
- [ ] Step 4: `urlsplit` で実装
- [ ] Step 5: 成功を確認しコミット

### Task 2: HTML 解析（R1, R2）

**Files:**
- Create: `backend/app/batch/parser.py`、`backend/tests/fixtures/hot100.html`（実ページから3行に縮めたもの）、`backend/tests/fixtures/top.html`
- Test: `backend/tests/test_parser.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) class ChartEntry: rank: int; title: str; artist: str`、`class ParseError(ValueError)`、`parse_hot100(html: str) -> list[ChartEntry]`、`find_latest_hot100_url(html: str) -> str`（`resolve_chart_url` を通した URL）

- [ ] Step 1: テスト: `test_parse_hot100_rows`（rank 1 "The Fate Of Ophelia"/"Taylor Swift"）、`test_parse_mixed_artist_markup`（"Loe Shimmy & Don Toliver"）、`test_parse_empty_raises`、`test_find_latest_hot100_url`、`test_find_latest_hot100_url_relative`、`test_find_latest_missing_raises`
- [ ] Step 2: 失敗確認 → BeautifulSoup（`html.parser`）で実装 → 成功確認 → コミット

### Task 3: HTTP 取得（N2, N4）

**Files:** Create `backend/app/batch/fetcher.py`; Test `backend/tests/test_fetcher.py`

**Interfaces:**
- Produces: `class FetchError(RuntimeError)`、`class Fetcher: __init__(self, transport: httpx.BaseTransport | None = None)`, `get(self, url: str) -> str`。`get` は `urlsplit(url).hostname == HOST` かつ https でなければ `FetchError`。

- [ ] Step 1: テスト（`httpx.MockTransport`）: `test_get_returns_text`、`test_redirect_is_error`（302 → FetchError）、`test_non_200_is_error`、`test_rejects_other_host`、`test_too_large_is_error`（2MB超）
- [ ] Step 2: 失敗確認 → 実装（`follow_redirects=False`, `timeout=10`, User-Agent 固定、ストリームで上限判定）→ 成功確認 → コミット

### Task 4: DB とバッチ実行（R1, R5, R6）

**Files:** Create `backend/app/config.py`, `backend/app/db.py`, `backend/app/batch/runner.py`, `backend/app/batch/__main__.py`; Test `backend/tests/test_runner.py`

**Interfaces:**
- Produces: `Settings`（frozen dataclass: `spotify_client_id, spotify_client_secret, redirect_uri, frontend_url, db_path`）と `load_settings() -> Settings`
- Produces: `class Database: __init__(self, path: str)`（`:memory:` 可、テーブル作成）、`add_source(url: str) -> int`、`get_source(id: int) -> dict | None`、`pending_ids() -> list[int]`、`mark_done(id, entries: list[ChartEntry])`、`mark_failed(id, error: str)`、`tracks(id) -> list[ChartEntry]`
- Produces: `process_source(db: Database, source_id: int, fetcher: Fetcher) -> list[ChartEntry]`（失敗時は `mark_failed` してから元の例外を再送出）、`process_pending(db, fetcher) -> dict[int, str]`（id → status）
- CLI: `python -m app.batch [--add URL]`

- [ ] Step 1: テスト（フェイク Fetcher）: `test_process_hot100_source`、`test_process_top_source_follows_latest`、`test_invalid_url_marked_failed`、`test_fetch_error_marked_failed`、`test_process_pending_handles_all`
- [ ] Step 2: 失敗確認 → 実装 → 成功確認 → コミット

### Task 5: セッションと Spotify クライアント（R14, R15, N1, N5, N6）

**Files:** Create `backend/app/sessions.py`, `backend/app/spotify.py`; Test `backend/tests/test_spotify.py`, `backend/tests/test_sessions.py`

**Interfaces:**
- Produces: `@dataclass class Session: access_token: str; refresh_token: str; expires_at: float; user_id: str; display_name: str`、`class SessionStore: create(s: Session) -> str`, `get(sid: str) -> Session | None`, `delete(sid: str) -> None`
- Produces: `class SpotifyError(RuntimeError)`（`status: int`）、`class SpotifyClient: __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None, sleep=asyncio.sleep)`
  - `authorize_url(state: str) -> str`
  - `async exchange_code(code: str) -> TokenSet`、`async refresh(refresh_token: str) -> TokenSet`（`TokenSet = (access_token, refresh_token, expires_at)` の dataclass。refresh で新 refresh_token が無ければ旧値を引き継ぐ）
  - `async me(token) -> dict`
  - `async build_playlist(session: Session, name: str, tracks: list[TrackQuery]) -> PlaylistResult`（`TrackQuery(title, artist)`、`PlaylistResult(playlist_id, url, added, not_found: list[TrackQuery])`）。期限切れ（`expires_at - 60 < now`）なら先に refresh して session を更新。
  - `primary_artist(artist: str) -> str`（`Featuring|Feat.|&|,| X |:` の前）

- [ ] Step 1: テスト（`httpx.MockTransport` で accounts/api をモック、sleep はフェイク）: `test_authorize_url_params`（scope=playlist-modify-private, state, redirect_uri）、`test_exchange_code_uses_basic_auth`、`test_primary_artist`、`test_build_playlist_skips_not_found_keeps_order`、`test_fallback_query_used`、`test_items_added_in_chunks_of_100`、`test_retry_after_on_429`（3回まで、4回目で SpotifyError）、`test_refreshes_expired_token`、`test_session_store_roundtrip`
- [ ] Step 2: 失敗確認 → 実装（検索は Semaphore(5)）→ 成功確認 → コミット

### Task 6: API — チャート取得と Origin 検査（R7〜R9, N3）

**Files:** Create `backend/app/main.py`; Test `backend/tests/test_api_charts.py`, `backend/tests/conftest.py`

**Interfaces:**
- Produces: `create_app(settings: Settings, db: Database, fetcher: Fetcher, spotify: SpotifyClient, sessions: SessionStore) -> FastAPI`、モジュール変数 `app`（`load_settings()` から生成、uvicorn 用）
- `POST /api/charts` 応答 `{"id": int, "url": str, "tracks": [{"rank","title","artist"}]}`。エラーは `{"detail": str}`。

- [ ] Step 1: テスト: `test_post_chart_returns_tracks`、`test_post_chart_invalid_url_400`、`test_post_chart_fetch_error_502`、`test_post_rejects_foreign_origin_403`、`test_post_allows_same_origin`
- [ ] Step 2: 失敗確認 → 実装 → 成功確認 → コミット

### Task 7: API — 認証（R10〜R13, R17）

**Files:** Modify `backend/app/main.py`; Test `backend/tests/test_api_auth.py`

**Interfaces:**
- Cookie: `oauth_state`（HttpOnly, SameSite=Lax, max_age=600, path=/auth）、`sid`（HttpOnly, SameSite=Lax, path=/）。`Secure` は `frontend_url` が https のとき。

- [ ] Step 1: テスト: `test_login_redirects_and_sets_state`、`test_callback_state_mismatch_400`、`test_callback_missing_state_cookie_400`、`test_callback_success_sets_sid_and_redirects`、`test_me_unauthenticated`、`test_me_authenticated`、`test_logout_clears_session`
- [ ] Step 2: 失敗確認 → 実装 → 成功確認 → コミット

### Task 8: API — プレイリスト作成（R14〜R16）

**Files:** Modify `backend/app/main.py`; Test `backend/tests/test_api_playlists.py`

- [ ] Step 1: テスト: `test_create_playlist_201`（`{playlist_id,url,added,not_found}`）、`test_create_playlist_unauthenticated_401`、`test_create_playlist_validation_422`（tracks 0件 / 101件 / name 空）、`test_create_playlist_spotify_error_502`
- [ ] Step 2: 失敗確認 → 実装 → 成功確認 → コミット

### Task 9: フロントエンド土台とログイン状態表示（R18〜R20）

**Files:** Create `frontend/package.json`, `next.config.ts`, `tsconfig.json`, `vitest.config.ts`, `vitest.setup.ts`, `eslint.config.mjs`, `app/layout.tsx`, `app/page.tsx`, `app/globals.css`, `lib/api.ts`, `components/AuthStatus.tsx`; Test `frontend/__tests__/AuthStatus.test.tsx`, `frontend/__tests__/api.test.ts`

**Interfaces:**
- Produces（`lib/api.ts`）: `class ApiError extends Error { status: number }`、`type Me = {authenticated: false} | {authenticated: true; id: string; display_name: string}`、`getMe(): Promise<Me>`、`logout(): Promise<void>`、`fetchChart(url: string): Promise<{id:number; url:string; tracks: Track[]}>`、`createPlaylist(name: string, tracks: {title:string; artist:string}[]): Promise<PlaylistResult>`
- Produces（`AuthStatus`）: props `{ me: Me | null; onLogout: () => void }`。状態は `page` 側のクライアントコンポーネント `components/App.tsx` が持つ。

- [ ] Step 1: `npm install`（next, react, react-dom, typescript, vitest, jsdom, @testing-library/react, @testing-library/jest-dom, @vitejs/plugin-react, eslint, eslint-config-next）
- [ ] Step 2: テスト: `api.test.ts`（エラー時 `ApiError` に `detail` が入る）、`AuthStatus.test.tsx`（未ログインで「Spotifyでログイン」リンク `href="/auth/login"`、ログイン済みで表示名と「ログアウト」）
- [ ] Step 3: 失敗確認 → 実装 → 成功確認 → コミット

### Task 10: プレイリスト作成フォーム（R21〜R24）

**Files:** Create `frontend/components/PlaylistForm.tsx`, `frontend/components/App.tsx`; Test `frontend/__tests__/PlaylistForm.test.tsx`

**Interfaces:**
- `PlaylistForm` props `{ authenticated: boolean }`。URL 入力欄（ラベル「チャートURL」、初期値 `https://billboard.mryogaku.com/`）、ボタン「プレイリストを作成」。
- プレイリスト名: `ビルボード Hot 100-yyyy/mm/dd`（日付はURLのdate、なければ今日の日付）

- [ ] Step 1: テスト: `disabled_when_unauthenticated`、`creates_playlist_and_shows_result`（リンク・「95曲」・見つからなかった曲）、`shows_backend_error_detail`、`disabled_while_loading`（「作成中…」表示）
- [ ] Step 2: 失敗確認 → 実装 → 成功確認 → `npm run build` 成功確認 → コミット

### Task 11: 仕上げ（ドキュメント・ルート lint 設定）

**Files:** Create `portfolios/spotify-billboard-playlist/README.md`, `backend/.env.example`; Modify ルート `eslint.config.mjs`（`portfolios/**/.next/**`, `portfolios/**/node_modules/**`, `portfolios/**/.venv/**` を ignores へ）

- [ ] Step 1: README（日本語）: 概要、Spotify アプリ登録と Redirect URI `http://127.0.0.1:3000/auth/callback`、セットアップ、起動（`uvicorn app.main:app --env-file .env --port 8000`、`npm run dev`）、バッチ CLI、手動確認手順
- [ ] Step 2: ルートと本ディレクトリで `npm run lint`・`npm test`・`npm run build` が成功することを確認 → コミット
