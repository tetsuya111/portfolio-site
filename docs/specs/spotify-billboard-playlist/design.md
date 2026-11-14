# 設計: Billboard Hot 100 から Spotify プレイリストを作成する

要件: [requirements.md](requirements.md) ／ タスク: [tasks.md](tasks.md)

## TL;DR

`portfolios/spotify-billboard-playlist/` に、Python/FastAPI のバックエンド（スクレイピングバッチを同梱）と Next.js のフロントエンドを作る。フロントエンドは Next.js の rewrites でバックエンドを同一オリジンに見せ、Spotify OAuth（Authorization Code フロー）とトークン保持はすべてバックエンドが担う。チャートページは `dispHot100.php`（Hot 100 全順位の簡易表示ページ）に正規化してから取得・解析する。

## Non-Goals（技術面）

- 本番デプロイ・HTTPS 終端・複数プロセスでのセッション共有（セッションはプロセス内メモリ）
- DB マイグレーションツールの導入（起動時に `CREATE TABLE IF NOT EXISTS` するだけ）
- E2E テスト（Spotify 実アカウントが必要なため。手動確認手順を README に書く）

## 全体構成

```
ブラウザ ──> Next.js (127.0.0.1:3000)
               ├─ /            画面（React）
               ├─ /api/*  ─rewrite─> FastAPI (127.0.0.1:8000) /api/*
               └─ /auth/* ─rewrite─> FastAPI (127.0.0.1:8000) /auth/*
FastAPI ──> app.batch（スクレイピング） ──> billboard.mryogaku.com
        ──> SQLite（chart_sources / chart_tracks）
        ──> Spotify Accounts / Web API
```

同一オリジン化により、セッションCookie（`HttpOnly; SameSite=Lax`）がそのまま使え、CORS 設定が不要になる。Spotify の Redirect URI は `http://127.0.0.1:3000/auth/callback`（Spotify は `localhost` を禁止し、ループバックIPのみ HTTP を許可しているため）。

### ディレクトリ

```
portfolios/spotify-billboard-playlist/
  package.json            test / lint / build をまとめて実行する（backend+frontend）
  scripts/run-python.mjs  backend/.venv の Python を OS 非依存で呼ぶ
  README.md
  backend/
    pyproject.toml        依存・ruff・pytest 設定
    .env.example
    app/
      config.py           環境変数の読み込み
      db.py               SQLite 接続とテーブル作成・CRUD
      batch/
        urls.py           URL検証・正規化
        parser.py         HTML解析
        fetcher.py        HTTP取得（ホスト制限・タイムアウト）
        runner.py         DBの未処理URLを処理
        __main__.py       `python -m app.batch` のCLI
      spotify.py          Spotify API クライアント
      sessions.py         メモリ内セッションストア
      main.py             FastAPI ルーティング
    tests/                pytest（fixtures/ に実ページから縮めたHTML）
  frontend/
    package.json, next.config.ts, tsconfig.json, vitest.config.ts, eslint.config.mjs
    app/layout.tsx, app/page.tsx
    components/App.tsx（状態管理）, AuthStatus.tsx, PlaylistForm.tsx
    lib/api.ts            バックエンド呼び出し
    __tests__/            vitest + Testing Library
```

## バッチ（R1〜R6）

### URL の検証・正規化（`urls.py`、R2〜R4・N2）

`resolve_chart_url(url) -> ChartTarget` を返す。`ChartTarget` は「トップページ」「日付付き Hot 100 ページ」「その他の同一ホストのページ」のいずれか。

| 入力パス（スキームは https/http、ホストは `billboard.mryogaku.com` 固定） | 結果 |
|---|---|
| `/`、`/index.php`、`/s/`（フラグメント `#…` は無視） | トップページ |
| `/php/chart.php?date=D`、`/php/dispHot100.php?date=D`、`/s/php/…` の同名 | `https://billboard.mryogaku.com/php/dispHot100.php?date=D` |
| 上記以外の同一ホストのパス（例: `/php/artist.php?artist=…`） | `https://billboard.mryogaku.com<パス>?<クエリ>`（フラグメントは除く）をそのまま取得する。`<script>` 内に `$('#data-table').append(…)` がある詳細表示形式なら `parse_detail_page` で、なければ Hot 100 と同じセレクター（`table tbody tr` の順位・曲名 `<b>`）で解析する（`parse_chart_page` が中身で振り分ける）。曲が1件も取れなければ `ParseError`。詳細は [spotify-detail-page-scraping/design.md](../spotify-detail-page-scraping/design.md) |
| `chart.php`・`dispHot100.php` で `D` が `YYYY-MM-DD` でない、ホスト不一致、ユーザー情報・ポート指定付き | `InvalidChartUrl` |

取得は常に `https://` で行う。`chart.php` は曲データをJavaScript文字列で埋め込み上位40曲しか持たないため、同日付の `dispHot100.php`（素直な `<table>` で100曲）に寄せる（2026-11-13 に実ページで構造を確認）。その他のページは同じ表構造であれば使える。ランキング系ページ（`alltime.php` など）のように曲を `<script>` に埋め込んだ詳細表示形式なら `parse_detail_page` で解析する。詳細は [docs/specs/spotify-detail-page-scraping/design.md](../spotify-detail-page-scraping/design.md)。

曲数が100を超えるページでは、フロントエンドが先頭100曲だけを `POST /api/playlists` に送り、その旨を結果に表示する。

### 取得（`fetcher.py`、N2・N4）

- `httpx.Client(follow_redirects=False, timeout=10)`。3xx・非200 は `FetchError`。
- 応答サイズは 2 MB で打ち切る（実ページは約24 KB）。
- テストでは `httpx.MockTransport` を注入する。

### 解析（`parser.py`、R1・R2）

- `parse_hot100(html) -> list[ChartEntry]`: `table > tbody > tr` ごとに、1列目の `<b>` を順位、3列目の `<b>` を曲名、`<br>` 以降のテキストをアーティスト名とする（アーティストは `<a>` を含む場合と含まない場合があるため `get_text()` で連結し空白を正規化）。1件も取れなければ `ParseError`。
- `find_latest_hot100_url(html) -> str`: トップページの `a[href*="dispHot100.php?date="]` を探し、`resolve_chart_url` に通して返す（ページ内のリンクも検証してから辿る）。

### DB（`db.py`、R1・R5・R6）

SQLite（標準ライブラリ `sqlite3`）。パスは環境変数 `DB_PATH`（既定 `backend/data/app.db`）。

```sql
chart_sources(id INTEGER PK, url TEXT, status TEXT CHECK(status IN ('pending','done','failed')),
              error TEXT, created_at TEXT, fetched_at TEXT)
chart_tracks(source_id INTEGER REFERENCES chart_sources(id), rank INTEGER, title TEXT, artist TEXT,
             PRIMARY KEY(source_id, rank))
```

### 実行（`runner.py`・`__main__.py`）

- `process_source(db, source_id, fetcher)`: URL 解決→（トップなら最新週URLを取得）→取得→解析→`chart_tracks` 保存→`done`。例外は `failed` と `error` に記録（R5）し、呼び出し元へ結果を返す。
- `process_pending(db, fetcher)`: `pending` を古い順にすべて処理（R6）。CLI は `python -m app.batch`（`--add URL` で登録もできる）。

## バックエンド API（R7〜R17）

| メソッド・パス | 説明 | 主な応答 |
|---|---|---|
| `POST /api/charts` `{url}` | URL を `pending` で登録し、その場で `process_chart_page` を実行（R7） | 200 `{id, url, title, tracks:[{rank,title,artist}]}`（`title` はページ名） ／ 400 不正URL（R8）／ 502 取得・解析失敗（R9） |
| `GET /auth/login` | `state` を生成し `oauth_state` Cookie（HttpOnly, 10分）に保存、Spotify 認可URLへ 302（R10） | 302 |
| `GET /auth/callback?code&state` | `state` を Cookie と `secrets.compare_digest` で照合（R12）→トークン交換→`GET /me`→セッション作成、`sid` Cookie を設定し `FRONTEND_URL` へ 302（R11） | 302 ／ 400 |
| `GET /api/me` | ログイン状態（R13） | `{authenticated:false}` ／ `{authenticated:true, id, display_name}` |
| `POST /api/playlists` `{name, tracks:[{title,artist}]}` | 検索→作成→追加（R14・R15） | 201 `{playlist_id, url, added, not_found:[{title,artist}]}` ／ 401（R16） |
| `POST /auth/logout` | セッション破棄・Cookie 削除（R17） | 204 |

入力制約: `url` は 2048 文字以下、`tracks` は 1〜100 件、`name` は 1〜100 文字、`title`/`artist` は各 200 文字以下（Pydantic で検証、違反は 422）。

### Origin 検査（N3）

`POST` のエンドポイントは、`Origin` ヘッダがあれば `FRONTEND_URL` のオリジンと一致することを要求し、不一致なら 403。rewrites 経由でもブラウザが付けた `Origin` はそのまま届く。`SameSite=Lax` と合わせて CSRF を防ぐ。

### Spotify クライアント（`spotify.py`、R14・N5・N6）

- 認可URL: `https://accounts.spotify.com/authorize`、`response_type=code`、`scope=playlist-modify-private`、`state`、`redirect_uri`。
- トークン: `POST https://accounts.spotify.com/api/token`（Basic 認証でクライアント資格情報、`grant_type=authorization_code` / `refresh_token`）。
- 検索: `GET /v1/search?type=track&limit=1&q=track:"<曲名>" artist:"<主アーティスト>"`。ヒットなしなら `q=<曲名> <主アーティスト>` で再検索。主アーティストは `Featuring`・`&`・`,`・`X`・`:` 等の区切りより前の部分。
- 作成: `POST /v1/me/playlists` `{name, public:false, description}`（2026-11-13 時点のリファレンスで確認）。
- 追加: `POST /v1/playlists/{id}/items` `{uris}` を 100 件ずつ（同上）。
- 429: `Retry-After` 秒（上限 30 秒）待って最大3回再試行。401 はトークンを1回リフレッシュして再試行。
- 検索は `asyncio.Semaphore(5)` で並行数を制限し、結果はチャート順に並べ直す。

### セッション（`sessions.py`、N1）

`sid` は `secrets.token_urlsafe(32)`。値はメモリ内 dict に `{access_token, refresh_token, expires_at, user_id, display_name}` を保持。トークンはブラウザに返さない。`expires_at` の60秒前を過ぎたら使用前にリフレッシュ。

## フロントエンド（R18〜R24）

単一ページ（`app/page.tsx` はサーバーコンポーネントで枠だけ描画し、状態を持つ部分はクライアントコンポーネント）。

```
┌──────────────────────────────────────────────┐
│ Billboard → Spotify Playlist                 │
│ [● ログイン中: tetsu]  [ログアウト]           │  ← 未ログイン時は [Spotifyでログイン]
│ チャートURL: [https://billboard.mryogaku.com/ ]│
│ [プレイリストを作成]                           │  ← 未ログイン・処理中は disabled
│ 作成しました: <リンク>  追加 95曲               │
│ 見つからなかった曲: ・Title / Artist ...       │
└──────────────────────────────────────────────┘
```

- `AuthStatus`: マウント時に `GET /api/me`。ログインは `<a href="/auth/login">`（ページ遷移）、ログアウトは `POST /auth/logout` 後に再取得。
- `PlaylistForm`: 送信で `POST /api/charts` → 成功なら `POST /api/playlists`（名前は `{ページ名}-yyyy/mm/dd` 形式で自動生成。ページ名は `POST /api/charts` が返す `title`＝解析したページの `<title>` から「｜サイト名」以降を除いたもの、日付は末尾に付けるため、ページ名内の日付表記（`（2025年11月15日付）`・`2025/11/15`・`2025-11-15` など。括弧で囲まれていれば括弧ごと）は除く。何も残らなければ `ビルボード Hot 100`。名前が100文字を超えないようページ名を切り詰める。日付はURLの `date`、なければ今日）。各段階の失敗時はバックエンドの `detail` を表示（R23）。
- `lib/api.ts`: `fetch` の薄いラッパー。エラー時は `ApiError(status, detail)` を投げる。
- `next.config.ts` の `rewrites` で `/api/:path*`・`/auth/:path*` を `BACKEND_URL`（既定 `http://127.0.0.1:8000`）へ。

## 検討した代替案

- **フロントエンドで PKCE を完結させ、トークンをブラウザに置く**: バックエンドを経由せず簡単だが、トークンがブラウザの JS から読めるため N1 に反する。メモも「バックエンドが OAuth に対応」としているので不採用。
- **CORS を設定してフロントとバックエンドを別オリジンで通信**: Cookie に `SameSite=None; Secure` が必要になり、HTTP のローカル開発で成立しない。rewrites による同一オリジン化を採用。
- **`chart.php` を直接解析**: JS 文字列内の HTML を取り出す必要があり壊れやすく、40曲しかない。`dispHot100.php` への正規化を採用。
- **バッチを別プロセス・ジョブキューにして非同期処理**: 1件の取得は1リクエスト（約24 KB）で終わるため過剰。APIからは同期で `process_source` を呼び、未処理分のまとめ処理は CLI で行う。
- **ORM（SQLAlchemy）**: テーブル2つで標準 `sqlite3` で足りるため不採用。

## 横断的関心事

- **セキュリティ・プライバシー**: 取得先ホストを固定しリダイレクト非追従（SSRF 対策、N2）。トークン・シークレットはサーバー側のみ（N1）。OAuth `state` 検証（R12）、POST の Origin 検査と `SameSite=Lax`（N3）。`.env` は Git 管理外、`.env.example` のみ置く。Cookie の `Secure` は `FRONTEND_URL` が https のとき付ける。外部HTMLのテキストは React の通常描画でエスケープされる（`dangerouslySetInnerHTML` 不使用）。
- **パフォーマンス・スケーラビリティ**: 1回の作成で Spotify 検索が最大200回。並行5で数十秒程度を想定し、画面は処理中表示（R24）。単一ユーザー想定のためスケールは考慮しない。
- **オブザーバビリティ**: バックエンドは `logging` で取得URL・失敗理由・Spotify API のステータスを INFO/WARNING 出力（トークンは出力しない）。バッチの失敗理由は DB の `error` 列に残る。
- **テスト戦略**: バックエンドは pytest。HTML 解析は実ページを縮めたフィクスチャ、HTTP は `httpx.MockTransport`、API は FastAPI `TestClient` で Spotify・取得部分を差し替える。フロントは vitest + Testing Library で `fetch` をモック。実 Spotify との結合は README の手動手順で確認。
- **ロールアウト計画**: 新規の独立ディレクトリで既存部分への影響なし。ロールバックはディレクトリ削除で完了。

## 既存アーキテクチャとの整合性

リポジトリには既存のアプリコードがなく、規約は `portfolios/<プロジェクト名>/` に閉じることのみ。ルートの `eslint.config.mjs` は JS のみ対象のため、生成物（`.next/` 等）を拾わないよう ignores にこのディレクトリの生成物を追加する。
