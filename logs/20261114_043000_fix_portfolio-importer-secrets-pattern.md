# 修正: secrets.ts などのソースファイルを誤って除外しない

## 何を

- 常に除外する `secrets.*` を、設定ファイル形式（json・yaml・toml・ini・env・txt）だけに絞った。

## なぜ

- `src/lib/secrets.ts` のような環境変数を読むだけのソースまで除外され、取り込んだプロジェクトのビルドが壊れるため（code-review 3周目の指摘）。
