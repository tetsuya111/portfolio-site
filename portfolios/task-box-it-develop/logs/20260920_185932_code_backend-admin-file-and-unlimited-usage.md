# 管理者をテキストファイルで識別し、管理者の使用量を無制限にした

対象: `.kiro/specs/token-usage-and-history-retention/tasks.md` のタスク1〜3

## 何を

- `backend/accounts/admins.py`（新規）: 管理者リストのファイル（`ADMIN_EMAILS_FILE`）を読み、メールアドレスで管理者かを判定する。前後の空白・大文字小文字は無視、空行と `#` の行は読み飛ばし。ファイルの更新日時でキャッシュする。読めない場合は「管理者なし」として警告ログのみ（ログインは止めない）。
- `backend/accounts/views.py`: Googleログインのたびに `sync_user_role()` で `role` / `is_staff` / `is_superuser` をファイルの内容に合わせる。
- `backend/accounts/management/commands/sync_admins.py`（新規）: 既存の全ユーザーへ一括反映。`set_admin.py` は削除（設定元をファイルに一本化）。
- `backend/accounts/checks.py`（新規）: `manage.py check --deploy` で、パスがコードのディレクトリ内を指す場合（W001）とファイルが無い場合（W002）に警告。
- `backend/agents/usage.py`: 管理者は `ensure_within_limit()` の対象外。`usage_summary()` に `remaining_percent`（切り捨て、残っていれば最低1%）と `unlimited` を追加。管理者は `limit` / `remaining_percent` が `null`。
- `backend/config/settings.py`: `ADMIN_EMAILS_FILE`（既定 `BASE_DIR/admin_emails.txt`）を追加。`DAILY_TOKEN_LIMIT` は 300000 のまま変更なし。
- `backend/.gitignore` に `admin_emails.txt` を追加。テスト（accounts/agents）を追加・更新。

## なぜ

管理者の指定をDBの中（管理コマンド）からファイル1か所に移し、管理者は自分の動作確認が上限で止まらないようにするため。認可の実体は既存の `User.role` のままにし、`IsAdminRole` を使う既存のコードには触れていない。

## 補足

- 開発用ログイン（`ALLOW_DEV_LOGIN`、DEBUG専用）は例外で、外部の設定なしに使えるようファイルを参照しない。design.md にもこの例外を明記した。
- 設定の確認は通常の `manage.py check` ではなくデプロイ向けチェック（`--deploy`）にした。通常の起動やテストで警告が鳴らないようにするため。design.md の記述もこれに合わせた。
