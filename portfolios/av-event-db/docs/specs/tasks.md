# タスク: AVイベント情報DBサイト（av-event-db）

要件: [requirements.md](requirements.md) ／ 設計: [design.md](design.md)

各タスクは「失敗するテストを書く → 実装 → テスト成功を確認 → コミット」の順に進める。パスは `portfolios/av-event-db/` からの相対パス。確認コマンドはこのディレクトリで実行する。

## T1. プロジェクトの土台（— / NFR-2）

- [ ] `package.json`・`scripts/run-backend.mjs`・`.gitignore`・`backend/pyproject.toml`・`backend/manage.py`・`backend/config/`（settings・urls）を作成する。
- [ ] テスト `backend/tests/test_health.py`: `GET /api/health/` が `{"status": "ok"}`、`DEBUG` 既定が False。
- [ ] `/api/health/` を実装する。
- 確認: `npm run test:backend`・`npm run lint:backend`

## T2. データモデル（REQ-1.2, REQ-2.1, REQ-3.2, REQ-4）

- [ ] テスト `backend/tests/test_models.py`: `normalized_title` の自動計算、`end_date` 未指定時は `start_date`、`end_date < start_date` で検証エラー、`EventSource.source_url` と `FetchedPage.url` の一意性。
- [ ] `backend/events/models.py`・マイグレーション・`admin.py` を作成する。
- 確認: `npm run test:backend`

## T3. 日付の解析（REQ-1.2）

- [ ] テスト `backend/tests/test_dates.py`: 年付き各形式、年なし（同年・翌年繰り上げ）、範囲（終了日）、時刻、読めない文字列で `None`。
- [ ] `backend/events/crawler/dates.py` を実装する。
- 確認: `npm run test:backend`

## T4. レーベンシュタイン距離と重複判定（REQ-3.1, REQ-3.4）

- [ ] テスト `backend/tests/test_dedupe.py`: 距離の既知値（`kitten`/`sitting`=3、空文字）、類似度、`normalize_title`、しきい値の境界、開催日違いは候補外、同一 `source_url` 優先。
- [ ] `backend/events/crawler/dedupe.py` を実装する。
- 確認: `npm run test:backend`

## T5. 抽出ルールとパーサ（REQ-1.1, REQ-1.2, NFR-4）

- [ ] テスト `backend/tests/test_parser.py`・`test_sources.py`: HTMLフィクスチャから detail／list モードで `RawEvent` を作る、複数要素・属性取得、相対URLの絶対化、`http(s)` 以外のリンクを捨てる、設定の必須項目欠落でエラー。
- [ ] `backend/events/crawler/sources.py`・`parser.py`・`sources.json` を実装する。
- 確認: `npm run test:backend`

## T6. HTTP取得とページログ（REQ-1.4〜1.6, REQ-2）

- [ ] テスト `backend/tests/test_fetcher.py`（`httpx.MockTransport`）: 取得とログ保存、成功済み詳細ページはリクエストなし、失敗済みは再取得、一覧は毎回取得、robots.txt 禁止で取得しない、例外・5xx で failed 記録、同一ホスト1秒間隔（待機関数のフェイク）。
- [ ] `backend/events/crawler/fetcher.py` を実装する。
- 確認: `npm run test:backend`

## T7. 会場の正規化とジオコーディング（REQ-4）

- [ ] テスト `backend/tests/test_venues.py`: 規則正規化（都道府県抽出）、エイリアスでノーマライザを再呼び出ししない、同名同住所の会場を再利用、Claude応答のJSON解析・不正応答のフォールバック（クライアントをフェイク）、ジオコーダ成功・失敗。
- [ ] `backend/events/crawler/venues.py` を実装する。
- 確認: `npm run test:backend`

## T8. 取り込み処理と管理コマンド（REQ-1.1, REQ-1.3, REQ-3.2, REQ-3.3）

- [ ] テスト `backend/tests/test_importer.py`・`test_fetch_events_command.py`: 新規作成、類似タイトルの統合（取得元追加・空項目補完・女優和集合）、別日は別イベント、`--source` 絞り込み、ページ失敗時も継続、件数の出力。
- [ ] `backend/events/crawler/importer.py`・`management/commands/fetch_events.py`・`seed_demo.py` を実装する。
- 確認: `npm run test:backend`

## T9. 読み取り専用API（REQ-5, REQ-6.1〜6.3, NFR-1, NFR-2）

- [ ] テスト `backend/tests/test_api.py`: 一覧の並び順・20件ページ分割、`q`（女優名・会場名を含む）、期間の重なり、都道府県、不正日付で400、詳細、地図APIの期間絞り込み・既定期間・366日超で400、POST が405、1,000件で1秒以内。
- [ ] `backend/events/serializers.py`・`views.py`・`urls.py` を実装する。
- 確認: `npm run test:backend`・`npm run lint:backend`

## T10. フロントエンドの土台と年齢確認（REQ-7, NFR-3）

- [ ] `frontend/` の `package.json`・Next/Vitest/ESLint 設定・`src/app/layout.tsx` を作成する。
- [ ] テスト: `AgeGate`（未確認で内容非表示、承認で表示・保存、保存済みなら省略、未満で案内）、`safeExternalUrl`、`mapsSearchUrl`、`api.ts` のクエリ組み立て。
- [ ] `src/components/AgeGate.tsx`・`src/lib/format.ts`・`src/lib/api.ts` を実装する。
- 確認: `npm run test:frontend`・`npm run lint:frontend`

## T11. 検索画面と詳細画面（REQ-5）

- [ ] テスト: `api.ts` のクエリ組み立て、`EventSearch`（フォーム送信でAPI呼び出し・一覧表示・該当なし・ページ送り）、`EventDetail`（全項目・取得元リンク）。
- [ ] `src/lib/api.ts`・`types.ts`・`src/components/EventSearch.tsx`・`EventDetail.tsx`・`src/app/page.tsx`・`src/app/events/page.tsx` を実装する。
- 確認: `npm run test:frontend`・`npm run lint:frontend`

## T12. 地図画面（REQ-6）

- [ ] テスト: `EventMap`（キー未設定で全会場のリンク一覧、座標なし会場をリンク一覧に出す、期間変更でAPI再取得、キーありでマップ読み込み関数を呼ぶ）。
- [ ] `src/lib/googleMaps.ts`・`src/components/EventMap.tsx`・`src/app/map/page.tsx` を実装する。
- 確認: `npm run test`・`npm run lint`・`npm run build`

## T13. ドキュメント

- [ ] `README.md`（日本語: 概要・セットアップ・環境変数・コマンド・抽出ルールの調整方法）を作成し、`docs/projects.md` に索引を追加する。
- 確認: リンク切れがないことを目視確認する。
