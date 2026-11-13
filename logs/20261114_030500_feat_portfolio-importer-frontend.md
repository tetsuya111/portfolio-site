# 機能: ポートフォリオ取り込みコマンドのフロントエンド配信登録

## 何を

- `importer/frontend.py` を追加した。配信可能なフロントエンドを `portfolio-site/apps/<スラッグ>/` にコピーし、`portfolio-site/apps/apps.json` に出力先・ビルド引数を登録する。既存のコピー・登録は変更しない。

## なぜ

- フロントエンドを portfolio-site 側で管理し、デプロイ時にまとめてビルド・S3 配信できるようにするため（要件 R2-1, R2-2）。
