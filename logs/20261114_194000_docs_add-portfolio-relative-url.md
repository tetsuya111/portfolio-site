# ドキュメント: 掲載 md の url の相対パス対応を記載

- 何を: `.claude/skills/add-portfolio/SKILL.md` からドメインを探して `--site-url` を補う手順を削除し、`portfolios/portfolio-importer/README.md`・`portfolio-site/docs/content-files.md` に相対パスの `url` を記載した。
- なぜ: issue #21。importer とスキーマが `/apps/<スラッグ>/` を扱うようになったため、手順と説明を合わせる。
