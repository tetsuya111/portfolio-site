# 修正: ポートフォリオ取り込みコマンドのレビュー指摘への対応

## 何を

- 生成する Dockerfile で、アプリのファイルの所有者を実行ユーザーに合わせた（Python: `COPY --chown=appuser`、node: `/app` を node 所有にしてから依存を入れる）。spotify の Dockerfile も再生成した。
- Next.js は `basePath: "/apps/<スラッグ>"` がなければ配信登録しない。SvelteKit・Nuxt・Remix などの Vite メタフレームワークと、サーバー出力の Astro も配信登録しない。
- 常に除外するものに `node_modules/`・`.venv/`・`venv/`・`__pycache__/`・`*.pyc`・鍵/証明書・`.npmrc`・`credentials*.json` を追加。フロントエンドを `apps/` にコピーするときもプロジェクトのルートの `.gitignore` を適用する。
- 起動コマンドの探索でテストを対象外にし、最初の一致で止めるようにした。README のタイトルはコードブロック外の最初の h1 から取り、本文からその行を除く。
- `apps/` の二重管理とビルド失敗時の挙動を `portfolio-site/docs/apps.md` に明記し、要件・設計を更新。

## なぜ

- code-review の指摘のうち、実コードで再現・妥当性を確認できたもの（コンテナの書き込み権限エラー、配信後にリソースが 404 になる登録、依存・秘密情報の取り込み、誤った起動コマンド・タイトル）を直すため。
