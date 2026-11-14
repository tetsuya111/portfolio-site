# 特定のメールアドレスだけログインに失敗する問題を修正（GoogleのユーザーIDの変更に追従する）

## 何が起きていたか

`tetsuya1729@gmail.com` でログインすると、画面に「ログインできませんでした。もう一度お試しください。」と表示される。他のアドレスでは起きない。

`GoogleLoginView` はユーザーの同定にGoogleのユーザーID（`sub`）を使い、見つからなければ新規作成する。GoogleのユーザーIDはOAuthクライアントのプロジェクトごとに異なるため、クライアントを変えると同じ人でも別のIDになる。その場合、

1. `google_sub` では既存のユーザーが見つからない
2. 同じメールアドレスで新規作成しようとする
3. `accounts_user.email` の unique 制約に違反して `IntegrityError`（500）

という流れで失敗していた。フロントエンドはAPIのエラーを区別せず、すべて上記のメッセージにするため「ログインできませんでした」とだけ表示されていた。既にDBに行があるアドレス（今回は1件のみ）でしか起きないため、他のアドレスでは再現しなかった。

再現を `accounts/tests.py` に追加して確認した（修正前は `UNIQUE constraint failed: accounts_user.email`）。

## 直したこと

`backend/accounts/views.py` の `GoogleLoginView`: `google_sub` で見つからない場合、確認済みのメールアドレス（`email_verified` はトークン検証時に確認済み）で既存のユーザーを引き当て、新しい `google_sub` に紐づけ直すようにした。表示名の更新とあわせて、変更があったフィールドだけを保存する。

回帰テスト `test_existing_email_is_relinked_when_the_google_id_changes` を追加（同じメールアドレスのユーザーが二重に作られないことも確認）。

## 確認

`python manage.py test` 68件パス。

## 補足

- メールアドレスでの引き当ては、Googleが確認済みのメールアドレス（`email_verified=true`）に限られる。未確認のアドレスは `verify_google_credential` の時点で弾いている。
- もし修正後も同じメッセージが出る場合は、原因が別（トークンの検証失敗など）のため、バックエンドのコンソールの出力を確認する。
