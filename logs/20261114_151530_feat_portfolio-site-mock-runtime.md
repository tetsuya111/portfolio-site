# モックのランタイムを追加

- 何を: `portfolio-site/src/lib/mock-runtime.js`（ブラウザで `window.fetch` を差し替え、`portfolioMock.handle` で登録したメソッド・パスにハンドラーの戻り値で応答する）とテストを追加し、ESLint でブラウザのグローバルを許可した。
- なぜ: 取り込んだフロントエンドを、バックエンドを常駐させずに S3 だけで動かすため（docs/specs/add-portfolio-mock-backend の R3）。
