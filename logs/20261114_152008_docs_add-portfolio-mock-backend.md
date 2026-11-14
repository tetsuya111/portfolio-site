# /add-portfolio のスキル・ドキュメントをモック接続に合わせて更新

- 何を: `.claude/skills/add-portfolio/SKILL.md` からイメージ作成の手順・確認を削除し、「モックの仕上げ」（handlers.js に応答データを書く）を追加した。importer の README、`portfolio-site/docs/apps.md`（`mock` 項目・モックの仕組みと制約）、`docs/skills.md` を更新した。
- なぜ: 取り込み時にバックエンドを Docker で動かす代わりに、モックで S3 だけで動かすようになったため（docs/specs/add-portfolio-mock-backend の R5）。
