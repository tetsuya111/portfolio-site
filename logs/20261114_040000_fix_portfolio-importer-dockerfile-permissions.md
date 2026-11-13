# 修正: 生成する Dockerfile で実行ユーザーがアプリのファイルに書き込めるようにする

## 何を

- Python は `COPY --chown=appuser:appuser`、node は `/app` を node 所有にしてから依存を入れるようにした。spotify の Dockerfile も再生成した。

## なぜ

- root 所有のままだと、SQLite などのデータを書くアプリがコンテナ起動時に PermissionError で落ちるため（code-review 1周目の指摘）。
