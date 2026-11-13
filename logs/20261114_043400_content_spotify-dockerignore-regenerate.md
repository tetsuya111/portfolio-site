# コンテンツ: spotify-billboard-playlist の .dockerignore を再生成

## 何を

- 秘密情報のパターンを追加した後のテンプレートで `backend/.dockerignore` を作り直した。

## なぜ

- 既存ファイルは上書きしない仕様のため、古いテンプレートのまま鍵などがイメージに入りうる状態だったため（code-review 3周目の指摘）。
