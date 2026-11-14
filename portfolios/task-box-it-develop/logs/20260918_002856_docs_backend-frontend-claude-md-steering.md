# docs/ の新規作成と、CLAUDE.md・steering の更新

## 何を行ったか

- `docs/backend.md` / `docs/frontend.md` を新規作成した（セットアップ、コマンド、環境変数、アーキテクチャ、実装上の決まりごと、インフラへの申し送り事項）。
- `backend/README.md` / `frontend/README.md` を日本語で作成し、詳細は docs/ へのリンクにした。
- `CLAUDE.md` の「プロジェクト構成」「ドキュメント一覧」を実装後の状態に更新し、横断的な注意点に、ポートの衝突と、実際のLLMでの確認は了承を得てから行うことを追記した。
- `.kiro/steering/` の product.md（現状）、tech.md、structure.md を実装後の状態に更新した。

## なぜ行ったか

アプリ本体を作成したため。tasks.md のタスク1・2・19の完了条件であり、CLAUDE.md の「詳細は docs/ に一本化する」方針に従った。
