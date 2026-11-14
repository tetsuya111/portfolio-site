# 保持期間を過ぎた対話履歴を消すバッチを追加した

対象: タスク7

## 何を

- `backend/config/settings.py`: `CONVERSATION_RETENTION_DAYS`（既定30、環境変数で変更可）を追加。
- `backend/chat/retention.py`（新規）: 最後のメッセージから保持期間を過ぎた対話を選び、既存の `clear_conversation()` で履歴を消す。メッセージのない対話と、実行中（ロックが有効）の対話は対象外。件数としきい値のみをログに出す。
- `backend/chat/management/commands/purge_conversations.py`（新規）: 上記を呼ぶだけのコマンド。`--dry-run` で消さずに件数を確認できる。
- テスト追加: 古い対話は消える / 新しい対話は残る / 使い続けていれば消えない / 確定済みの要件サマリーと使用量の記録は残る / 実行中は除外 / メッセージなしでもエラーにならない / dry-run では消えない / 2回実行しても変わらない / コマンドの出力。

## なぜ

対話履歴に消える契機が「クリア」しかなく、際限なく残り続けていたため。消去のロジックを2か所に分けないよう、バッチは既存の `clear_conversation()` を呼ぶだけにした。

## 確認

- `python manage.py purge_conversations --dry-run` と通常実行を開発環境で1回ずつ実施。対象0件（30日以上前の対話がないため）で、履歴は変化なし。
- 定期実行の設定はインフラ未定のため未実施。docs/backend.md の申し送り事項に記載した。
