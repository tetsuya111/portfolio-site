# 取り込み時にモックを接続し、Docker イメージ作成処理を削除

- 何を: `importer/cli.py`・`importer/frontend.py` を更新し、フロントエンドを配信登録してバックエンドがある場合に `apps/<スラッグ>/mock/handlers.js` の雛形を作り、`apps.json` に `"mock": true` を入れるようにした。`--build-image`・Dockerfile/.dockerignore の生成（`importer/backend.py`）とタグの `Docker` を削除した。出力 JSON は `frontend.mock`・`backend.routes` に変わった。
- なぜ: バックエンドを常駐させずに S3 だけで動かすため、Docker イメージは使わなくなる（docs/specs/add-portfolio-mock-backend の R1-7〜R1-9, R4）。
