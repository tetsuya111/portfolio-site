# 仕様: ポートフォリオ追加スキルの要件・設計・タスク作成

## 何を

- `docs/specs/add-portfolio/` に requirements.md・design.md・tasks.md を新規作成した。

## なぜ

- `memo/add_portfolio_to_portfolio-site.md` の要望（指定プロジェクトを `portfolios/` に取り込み、フロントエンドの S3 配信・バックエンドのコンテナ化・サイト掲載までを行うスキル）を、`/superpowers-create-from-design-to-pr` で無人実装するため。
- 主な判断: Python 標準ライブラリのみで実装（外部取得を避ける）、フロントエンドは既存バケットの `/apps/<スラッグ>/` に配信、Docker イメージの tar は git 管理外。
