# 機能: ポートフォリオ取り込みコマンドの掲載 md 作成

## 何を

- `importer/content.py` を追加した。`portfolios/docs/<スラッグ>.md` → README → スラッグの順で情報を集め、`portfolio-site/src/content/portfolios/<スラッグ>.md` をサイトのスキーマに合う frontmatter（値はダブルクォート文字列）で作成する。
- 本文先頭の h1 は除き、http/https 以外の URL・空の URL は入れない。既存ファイルは上書きしない。

## なぜ

- 取り込んだプロジェクトをポートフォリオサイトに掲載するため（要件 R4-1〜R4-4）。
