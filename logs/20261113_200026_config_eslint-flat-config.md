# ESLint 設定ファイルの作成

## 何を
- `eslint.config.mjs`（フラット設定）を新規作成。`@eslint/js` の recommended をベースに、`eqeqeq` / `prefer-const` / `no-var` 等を追加。
- `eslint` を dependencies から devDependencies に移動し、`@eslint/js` と `globals` を devDependencies に追加。

## なぜ
- `npm run lint` 実行時に「ESLint couldn't find an eslint.config.* file.」で失敗していたため。ESLint v9 以降はフラット設定のみをサポートする。
- `package.json` に `"type"` 指定がないため、ESM として確実に読み込まれる `.mjs` 拡張子を採用。
- 技術スタック未定のため JS の汎用設定に留め、TypeScript / フレームワーク用プラグインは確定後に追加する。
