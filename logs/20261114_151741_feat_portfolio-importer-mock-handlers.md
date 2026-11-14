# バックエンドのルート検出とモックの雛形生成を追加

- 何を: `portfolios/portfolio-importer/importer/mock.py` を追加した。バックエンドのソース（テストを除く）から FastAPI・Flask・Express 系のルートを検出し、`mock/handlers.js` にルートごとの `portfolioMock.handle` の雛形を書く。
- なぜ: 取り込んだフロントエンドをモックと接続するため、呼ばれる API の一覧を自動で用意する（docs/specs/add-portfolio-mock-backend の R1-1〜R1-6）。
