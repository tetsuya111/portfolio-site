# 機能: ポートフォリオ取り込みコマンドの Dockerfile 生成とイメージ作成

## 何を

- `importer/backend.py` を追加した。Python（uvicorn の記載・`FastAPI(` の代入・`main.py` から起動コマンドを判定）と node（`npm start`）の Dockerfile・.dockerignore を生成する。既存ファイルは上書きしない。
- 指定時のみ `docker build`・`docker save` で `portfolios/docker-images/<スラッグ>-backend.tar` を作る。tar は同ディレクトリの `.gitignore` で git 管理外にする。

## なぜ

- バックエンドを別 VPS でコンテナとして起動できるようにするため（要件 R3-1〜R3-3）。
