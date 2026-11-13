# 修正: コピー時の除外漏れを直す

## 何を

- 常に除外するものに依存・キャッシュ（`node_modules/`・`.venv/`・`venv/`・`__pycache__/`・`*.pyc`）と秘密情報（鍵・証明書、`.npmrc`、`credentials*.json`・`service-account*.json`・`secrets.*`・`id_rsa*` など）を追加し、生成する .dockerignore にも入れた。
- フロントエンドを `apps/` にコピーするときもプロジェクトのルートの `.gitignore` を適用し、ルートのフロントエンドではバックエンドのディレクトリを除くようにした。

## なぜ

- 依存や秘密情報がリポジトリ・Docker イメージに入り込むのを防ぐため（code-review 1・2周目の指摘）。
