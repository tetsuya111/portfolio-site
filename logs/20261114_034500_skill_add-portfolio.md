# スキル: add-portfolio を新規作成

## 何を

- `.claude/skills/add-portfolio/SKILL.md` を作成した（`/add-portfolio <パス>` で明示起動のみ）。`portfolio-importer` の実行、`docker build` など外部アクセスの事前確認、掲載 md の仕上げ、`portfolio-site` のテスト・lint による検証、作業ログ、報告までの手順を定めた。
- `portfolios/portfolio-importer/README.md` を追加し、`docs/skills.md`・`docs/projects.md` の一覧を更新した。

## なぜ

- 要望メモ（指定プロジェクトをポートフォリオとして追加するスキル）の入口として、コマンドだけでは判断できない仕上げと確認を Claude が行うため（要件 R5-1, R5-2）。
