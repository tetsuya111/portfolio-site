# 機能: importer が掲載 md の url を相対パスで保存する

- 何を: `portfolios/portfolio-importer/importer/cli.py` で、フロントエンドを配信登録したとき `--site-url` がなければ `url` を `/apps/<スラッグ>/` にした。`content.py` は http(s) の検証をメタデータ由来の `url` だけに適用するよう変更。テストを追加・更新。
- なぜ: issue #21。本番ドメインを掲載 md に書かず、本番・dev の各サイトで自分の環境のアプリを開けるようにするため。
