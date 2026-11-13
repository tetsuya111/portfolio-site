# 修正: Tailwind が apps/ のファイルを走査しないようにする

## 何を

- `src/styles/global.css` に `@source not "../../apps";` を追加した。

## なぜ

- 取り込んだフロントエンドのクラスがサイトの CSS に混ざり、サイズ増加や意図しないスタイルの原因になるため（code-review 3周目の指摘）。
