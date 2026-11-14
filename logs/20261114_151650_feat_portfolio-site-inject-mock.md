# apps.json の mock でビルド成果物にモックを差し込む

- 何を: `apps.json` の項目に任意の `mock`（真偽値）を追加した。true のアプリは `npm run build:apps` で、ランタイムと `mock/handlers.js` を `dist/apps/<スラッグ>/__mock__/` に置き、すべての HTML の `<head>` 直後に読み込みの `<script>` を差し込む。
- なぜ: アプリのソースを書き換えずに、どのフレームワークの静的出力にもモックを接続するため（docs/specs/add-portfolio-mock-backend の R2）。
