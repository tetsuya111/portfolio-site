# 機能: ポートフォリオ取り込みコマンドの除外判定

## 何を

- `portfolios/portfolio-importer/` を新規作成し、`.gitignore` 互換の除外判定（`importer/ignore.py`）とテストを追加した。
- `.git/`・DB ファイル（`*.sqlite` など）・`.env` 系（`.env.example` を除く）・シンボリックリンクは常に除外する。

## なぜ

- 指定プロジェクトを `portfolios/` にコピーする際に、ビルド成果物・非初期データ・秘密情報を持ち込まないため（要件 R1-3, R1-4）。
