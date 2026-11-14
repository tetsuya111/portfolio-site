# 相対パスの url 保存 実装計画

> **For agentic workers:** superpowers:test-driven-development で1タスクずつ進める。

**Goal:** 配信登録したフロントエンドの掲載 md の `url` を `/apps/<スラッグ>/` で保存し、サイトのスキーマで受け付ける。

**Spec:** [requirements.md](requirements.md)・[design.md](design.md)

## Global Constraints

- テスト: `portfolios/portfolio-importer` で `npm test`・`npm run lint`、`portfolio-site` で `npm test`・`npm run lint`。

---

### Task 1: スキーマでサイト内パスを受け付ける（R2-1, R2-2, R2-3）

**Files:** Modify `portfolio-site/src/lib/schemas.ts`, Test `portfolio-site/tests/schemas.test.ts`

- [ ] テスト: `/apps/x/` を受理 / `//evil.com`・`/\evil.com`・`/a b`・`/a\b`・`/a%0a` 以外の改行入り・`javascript:alert(1)` を拒否 / `profileSchema.links` の `/x` を拒否
- [ ] 失敗確認 → 実装 → `npm test`・`npm run lint` 成功 → コミット

### Task 2: importer が相対パスを保存する（R1-1〜R1-3）

**Files:** Modify `portfolios/portfolio-importer/importer/cli.py`, `importer/content.py`, Test `tests/test_cli.py`, `tests/test_content.py`

- [ ] テスト: `--site-url` なしで `url: "/apps/my-app/"` / `--site-url` ありで絶対 URL（既存） / `write_portfolio_md` に `app_url="/apps/my-app/"` で保存 / メタデータの `url: /foo` は捨てる
- [ ] 失敗確認 → 実装 → `npm test`・`npm run lint` 成功 → コミット

### Task 3: スキル・README の更新（R3-1）

**Files:** Modify `.claude/skills/add-portfolio/SKILL.md`, `portfolios/portfolio-importer/README.md`

- [ ] `--site-url` を任意（既定は相対パス）と記載し、スキルのドメイン探索手順を削除
- [ ] コミット
