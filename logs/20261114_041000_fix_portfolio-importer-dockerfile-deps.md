# 修正: 生成する Dockerfile の依存インストールとビルド手順

## 何を

- Python は `requirements.txt` を優先し、`pyproject.toml` は `[project]` があるときだけ `pip install .` する。
- node は `build` スクリプトがあれば開発用の依存も入れてビルドし、`npm prune --omit=dev` で除く。スクリプト判定は detect の `has_script` を共用。

## なぜ

- ツール設定だけの pyproject で依存が入らない、ビルドが必要な TypeScript のバックエンドが起動できない問題を防ぐため（code-review 2周目の指摘）。
