# 管理者として認識されない問題の調査と修正（ファイルの置き場所 / 開発用ログインの権限）

## 何が起きていたか

`tetsuya1729@gmail.com` でログインしても管理者にならなかった。

- 管理者リストのファイルがリポジトリのルート（`task_box_it_develop/admin_emails.txt`）に置かれていたが、アプリが読むのは `ADMIN_EMAILS_FILE` の既定値である `backend/admin_emails.txt`。ファイルが見つからず「管理者は1人もいない」として扱われ、ログインのたびに `role=general` に同期されていた。
- Googleログイン自体は成功していた（API は 200 を返していた）。失敗して見えたのは、管理者向けの画面・APIに入れなかったため。
- ルートの `admin_emails.txt` は `backend/.gitignore` の対象外でもあり、メールアドレスがコミットされうる状態だった。

## 直したこと

- `admin_emails.txt` を `backend/admin_emails.txt`（既定のパス、`backend/.gitignore` の対象）へ移動し、末尾に改行を補った。`python manage.py sync_admins` を実行して権限を反映（role=admin / is_staff / is_superuser）。
- `backend/accounts/views.py` の開発用ログイン（`DevLoginView`）を修正。`get_or_create` の `defaults` は新規作成時しか効かないため、`sync_admins` で権限を落とされた開発用の管理者アカウント（`dev-admin@example.com`）が、再ログインしても一般ユーザーのままになっていた。毎回、要求された権限にそろえるようにした。
- 上記の回帰を防ぐテストを `accounts/tests.py` に追加（`test_dev_login_restores_admin_after_sync_admins`）。

## 確認

- `python manage.py test` 67件パス。
- Googleログインを模したリクエストで `role=admin` になり、`GET /api/admin/summaries/` が 200 になることを確認。

## 補足

- 本番ではコードのディレクトリの外（例: `/etc/task-box/admin_emails.txt`）に置き、`ADMIN_EMAILS_FILE` で指定する（docs/backend.md「管理者の指定」）。ルートに置いたままにしたい場合は `backend/.env` に `ADMIN_EMAILS_FILE` を設定する必要がある。
