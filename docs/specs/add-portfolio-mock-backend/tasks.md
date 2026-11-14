# 取り込んだフロントエンドのモック接続 実装計画

要件: [requirements.md](requirements.md) ／ 設計: [design.md](design.md)

## Global Constraints

- importer は Python 3.12 標準ライブラリのみ。テストは `cd portfolios/portfolio-importer && npm test`・`npm run lint`。
- portfolio-site のテストは `cd portfolio-site && npm test`・`npm run lint`（出力は `| tail -30` で失敗箇所だけ確認）。
- 各タスクは失敗するテスト → 実装 → テスト成功 → コミット。`logs/` に作業ログを1件ずつ書く。

## Tasks

### Task 1: モックのランタイム（R3-1〜R3-8）

- 対象: `portfolio-site/src/lib/mock-runtime.js`（新規）、`portfolio-site/tests/mock-runtime.test.ts`（新規）
- [ ] テスト: GET の一致で通信せず JSON 200 / 戻り値 undefined で 204 / Response はそのまま / `:id` の値が params に入る / query と JSON 本文が渡る / `/apps/<slug>/api/x` が `/api/x` に一致 / 別オリジンの URL も一致 / メソッド違い・一致なしは元の fetch / 例外で 500 / async の戻り値
- [ ] 失敗確認 → 実装 → 成功 → コミット

### Task 2: ビルドでの接続（R2-1〜R2-4）

- 対象: `portfolio-site/src/lib/apps-manifest.ts`、`portfolio-site/scripts/build-apps.mjs`、`portfolio-site/tests/apps-manifest.test.ts`
- [ ] テスト: `mock` 省略で false・true を受け付け・文字列はエラー / mock なら `__mock__/runtime.js`・`handlers.js` を置き、入れ子の html も含め `<head>` 直後に2つの script を差し込む / `<HEAD lang>` も対象 / head がなければ doctype の後 / mock なしなら差し込まない / handlers.js がなければビルド前にエラー
- [ ] 失敗確認 → 実装 → 成功 → コミット

### Task 3: ルートの検出と雛形の生成（R1-1〜R1-6）

- 対象: `portfolios/portfolio-importer/importer/mock.py`（新規）、`tests/test_mock.py`（新規）
- [ ] テスト: FastAPI の `@app.get("/api/me")`・複数行の `@app.post(\n "/x"` / `@router.delete("/items/{item_id}")` → `:item_id` / Flask `@app.route("/x/<int:id>", methods=["GET", "POST"])` → 2件・`:id` / Flask methods なし → GET / express `router.post('/api/x', ...)`・テンプレート文字列 / tests 配下・`test_*.py`・`*.test.js` は無視 / 重複は1件 / 雛形に各ルートの `portfolioMock.handle` / 0件なら例だけで警告 / 既存なら上書きせず警告
- [ ] 失敗確認 → 実装 → 成功 → コミット

### Task 4: CLI・登録の更新と Docker 処理の削除（R1-7〜R1-9, R4-1〜R4-3）

- 対象: `importer/cli.py`、`importer/frontend.py`、`importer/backend.py`（削除）、`tests/test_backend.py`（削除）、`tests/test_cli.py`、`tests/test_frontend.py`
- [ ] テスト: 取り込みで `apps/<slug>/mock/handlers.js` ができ apps.json に `"mock": true` / 出力の `frontend.mock`・`backend.routes` / Dockerfile を作らない / `--build-image` はエラー / タグに Docker がない / バックエンドなしなら mock なし・項目に mock を入れない / 登録済みで mock なしなら警告
- [ ] 失敗確認 → 実装 → 成功 → コミット

### Task 5: ドキュメントとスキル（R5-1, R5-2）

- 対象: `.claude/skills/add-portfolio/SKILL.md`、`portfolios/portfolio-importer/README.md`、`portfolio-site/docs/apps.md`
- [ ] スキル: イメージ作成の手順・確認ルールの `--build-image` を削除し、「モックの仕上げ」（TODO のハンドラーにバックエンドのコードとフロントエンドの型から応答データを書く。router の prefix を確認する。ページ遷移は横取りできない）を追加。報告項目を更新
- [ ] README・apps.md: モックの仕組み・書式・制約（fetch のみ・dev では入らない・秘密情報を書かない）を記載し、Docker の記述を削除
- [ ] コミット

## 要件との対応

| 要件 | タスク |
|---|---|
| R1-1〜R1-6 | Task 3 |
| R1-7〜R1-9 | Task 4 |
| R2-1〜R2-4 | Task 2 |
| R3-1〜R3-8 | Task 1 |
| R4-1〜R4-3 | Task 4 |
| R5-1, R5-2 | Task 5 |
