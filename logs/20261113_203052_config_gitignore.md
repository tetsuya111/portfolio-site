# .gitignore の作成

## 何を

- プロジェクトルートに `.gitignore` を作成した。
  - 依存パッケージ（`node_modules/`）、ビルド成果物・キャッシュ、テスト結果、`*.log`、`.env` 系・鍵ファイル、エディタ・OSの生成ファイルを除外。
  - `.claude/settings.local.json`、`.opencodereview/config.json`・`sessions/` など個人設定・秘密情報を含みうるツール固有ファイルを除外。
  - 作業ログ `logs/*.md`、`.claude/settings.json`、`.env.example` などの共有ファイルは管理対象のまま残した。

## なぜ

- リポジトリにまだ `.gitignore` がなく、初回コミット時に `node_modules/` や秘密情報が混入するおそれがあったため。
- 技術スタックが未定のため、Node.js系の主要フレームワーク（Next.js / Astro / Nuxt など）の成果物を先回りして除外した。
