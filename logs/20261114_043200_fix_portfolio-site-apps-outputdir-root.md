# 修正: apps.json の outputDir にアプリのディレクトリ自体を指定できないようにする

## 何を

- `./`・`./.`・`dist/..` など、正規化するとアプリのルートになる outputDir を拒否するようにした。

## なぜ

- ソースや node_modules まで S3 に配信されるのを防ぐため（code-review 3周目の指摘）。
