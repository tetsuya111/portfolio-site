# 管理者の指定と対話履歴の保持について、ドキュメントとspecを更新した

対象: タスク8、および実装に合わせたspecの更新

## 何を

- `docs/backend.md`: コマンドの表（`sync_admins` / `purge_conversations` を追加、`set_admin` を削除）、環境変数の表（`ADMIN_EMAILS_FILE` / `CONVERSATION_RETENTION_DAYS` を追加、`DAILY_TOKEN_LIMIT` に管理者は対象外と明記）、「管理者の指定」の節を新設（ファイルの形式・反映の契機・本番での配置とパーミッション・開発用ログインの例外）、インフラへの申し送り事項に2点（管理者ファイルの配置、`purge_conversations` の定期実行）を追加。
- `docs/frontend.md`: `UsageIndicator` による残りの割合の表示を追記。
- `backend/.env.example`: `CONVERSATION_RETENTION_DAYS` と `ADMIN_EMAILS_FILE` を追加。
- `.kiro/specs/hearing-chat-site/design.md`: `set_admin` を前提にしていた3か所（role の設定方法、管理サイトの権限、リリース手順）を、管理者リストのファイルによる指定に更新。
- `.kiro/specs/token-usage-and-history-retention/`: requirements.md / design.md のステータスを「実装済み」に、tasks.md のチェックリストを完了にした（未完了は手作業での確認2件のみ）。

## なぜ

管理コマンドと環境変数が変わったため、ドキュメントを実装に合わせた。インフラが未定の2点（ファイルの配置、バッチの定期実行）は、設定されないと機能しないため申し送り事項として明記した。

## 残っていること

- 本番で管理者リストのファイルに切り替えたあと、管理者が管理者画面に入れることの確認（実環境が必要）。
- 実際のLLMでの確認（確定の統合後の判定精度）。費用がかかるため、ユーザーの了承を得てから行う。
