# 機能: portfolio-site でポートフォリオのフロントエンドを S3 配信する

## 何を

- `portfolio-site/apps/apps.json`（管理ファイル）と、その検証・ビルド処理（`src/lib/apps-manifest.ts`・`scripts/build-apps.mjs`・`npm run build:apps`）を追加した。
- 両 buildspec の build フェーズで `astro build` の後に `npm run build:apps` を実行し、成果物を `dist/apps/<スラッグ>/` に置く（既存の `s3 sync dist` で配信される）。
- CloudFormation テンプレートに出力 `AppsBaseUrl` を追加。`apps/` を ESLint・tsconfig の対象外にした。ドキュメント（`docs/apps.md` ほか）を更新。

## なぜ

- 取り込んだプロジェクトの node 製フロントエンドを、既存のスタック（S3 + CloudFront）から配信するため（要件 R2-3, R2-4）。PR 用 buildspec にも入れたのは、本番と同じ build コマンドを要求する既存テストに合わせ、アプリのビルド失敗をマージ前に検出するため。
