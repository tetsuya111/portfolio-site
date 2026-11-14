# 取り込んだフロントエンドのモック接続の設計を作成

- 何を: `docs/specs/add-portfolio-mock-backend/` に requirements.md・design.md・tasks.md を作成した。
- なぜ: `/add-portfolio` で取り込んだフロントエンドを、バックエンドを常駐させずに S3 だけで動かすため（調査メモ `memo/claude/add-portfolio_バックエンドのモック化調査.md`）。あわせて使われなくなる Docker イメージ作成処理を削除する。
- 判断: MSW は lockfile の更新に外部アクセスが必要なため使わず、依存のない fetch モックのランタイムを、ビルド時に HTML へ差し込む方式とした。
