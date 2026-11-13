# 設定: portfolio-importer の __pycache__ を管理対象から外す

## 何を

- 誤ってコミットした `importer/__pycache__/`・`tests/__pycache__/` の pyc を管理対象から外し、`portfolios/portfolio-importer/.gitignore`（`__pycache__/`・`*.pyc`）を追加した。

## なぜ

- Python のバージョンに依存するビルド成果物で、テストのたびに差分が出るため（code-review 1周目の指摘）。
