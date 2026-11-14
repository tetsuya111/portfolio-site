# バックエンド

Django REST Framework によるAPI。仕様は [.kiro/specs/hearing-chat-site/](../.kiro/specs/hearing-chat-site/design.md) を参照。

## セットアップ

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env          # 値を設定する（下の「環境変数」を参照）
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_agents
.\.venv\Scripts\python manage.py runserver
```

Python は 3.12 で動作を確認している。

## コマンド

| コマンド | 内容 |
| --- | --- |
| `python manage.py runserver [ポート]` | 開発サーバー（既定は8000） |
| `python manage.py test` | テスト。LLMは偽のクライアントに差し替わり、実際のAPIは呼ばない |
| `python manage.py seed_agents` | エージェント4つと初期テンプレ8つを登録する。既存の行は上書きしない |
| `python manage.py sync_admins` | 管理者リストのファイルの内容を、既存のすべてのユーザーの権限に反映する。通常はログイン時に反映されるため、ファイルによる指定に切り替えるときや、ログインを待たずに反映したいときに使う |
| `python manage.py purge_conversations` | 保持期間（`CONVERSATION_RETENTION_DAYS` 日）を過ぎた対話履歴を消す。1日1回の定期実行を想定。`--dry-run` を付けると消さずに対象の件数だけを表示する |
| `python manage.py changepassword <email>` | Djangoの管理サイト（`/django-admin/`）に入るためのパスワードを設定する。Googleで作られたユーザーはパスワードを持たないため、管理者は最初に1回実行する |

## 環境変数

`backend/.env` に書く（`.env.example` が雛形）。

| 変数 | 既定値 | 内容 |
| --- | --- | --- |
| `DEBUG` | `false` | 開発では `true` |
| `SECRET_KEY` | なし | `DEBUG=false` では必須 |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | カンマ区切り |
| `DATABASE_URL` | sqlite（`backend/db.sqlite3`） | 本番は PostgreSQL を想定 |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | フロントエンドのオリジン。フロントの `NEXT_PUBLIC_API_BASE_URL` と対で変える |
| `REFRESH_COOKIE_SECURE` | `DEBUG` の逆 | https で配信するなら `true` |
| `GOOGLE_OAUTH_CLIENT_ID` | なし | フロントの `NEXT_PUBLIC_GOOGLE_CLIENT_ID` と同じ値 |
| `ANTHROPIC_API_KEY` | なし | Anthropic SDK が読む |
| `LLM_MODEL` | `claude-sonnet-5` | |
| `LLM_EFFORT` | `medium` | `low` / `medium` / `high` / `xhigh` / `max` |
| `LLM_MAX_TOKENS` | `32000` | 1回の応答の上限 |
| `LLM_CLIENT_CLASS` | `agents.llm.AnthropicLLMClient` | `agents.demo.DemoLLMClient` にすると、APIキーなしで決まった応答を返す（画面の動作確認用） |
| `DAILY_TOKEN_LIMIT` | `300000` | 依頼者1人あたり1日（日本時間）のトークン数の上限。`0` にするとLLM呼び出しをすべて止められる。管理者はこの上限の対象外（無制限） |
| `CONVERSATION_RETENTION_DAYS` | `30` | 対話履歴の保持期間。最後のメッセージからこの日数が過ぎた対話履歴を `purge_conversations` で消す |
| `ADMIN_EMAILS_FILE` | `backend/admin_emails.txt` | 管理者のメールアドレスを列挙したテキストファイル（後述）。本番はコードの外の絶対パスを指定する |
| `EMAIL_BACKEND` ほか `EMAIL_*` | コンソール出力 | 本番はSMTPなどを設定する |
| `DEFAULT_FROM_EMAIL` | `noreply@localhost` | |
| `ADMIN_EMAIL` | なし | 要件サマリーの送信先。未設定だとメール送信は失敗として記録される |
| `ALLOW_DEV_LOGIN` | `false` | `DEBUG=true` のときだけ有効にできる開発用ログイン（`POST /api/auth/dev-login/`）。Googleの設定なしで画面を確認するためのもの |

## 管理者の指定

管理者は、Googleアカウントのメールアドレスを列挙したテキストファイル（`ADMIN_EMAILS_FILE`）で決まる。1行1メールアドレスで、前後の空白と大文字・小文字の違いは無視し、空行と `#` で始まる行はコメントとして読み飛ばす。

```
# タスク百葉箱の管理者
owner@example.com
```

- 反映されるのは**そのユーザーの次のログイン時**。ログイン中のユーザーにすぐ反映したい場合は `python manage.py sync_admins` を実行する。
- ファイルから消えたメールアドレスのユーザーは、次のログインで一般ユーザーに戻る。
- 権限の根拠になるファイルのため、**リポジトリにコミットしない**（`backend/.gitignore` に登録済み）。アプリケーションは読み取りしか行わない。
- **本番ではコードのディレクトリの外**（例: `/etc/task-box/admin_emails.txt`）に置き、`ADMIN_EMAILS_FILE` に絶対パスを設定する。デプロイでコードが置き換わっても消えないようにするため。パーミッションは所有者とアプリの実行ユーザーが読めるだけ（例: `0640`）に絞る。開発では既定値（`backend/admin_emails.txt`）のままでよい。
- ファイルが無い・読めない場合は「管理者が1人もいない」として扱い、警告をログに出すだけで依頼者の利用は止めない。設定の不備は `python manage.py check --deploy` で警告として検出できる。
- 開発用ログイン（`ALLOW_DEV_LOGIN`）だけは例外で、外部の設定なしに使えるよう、このファイルを参照せずに管理者を作る。

## アーキテクチャ

| アプリ | 役割 |
| --- | --- |
| `config/` | 設定、URL、エラー応答の統一（`exceptions.py`）、テスト共通の土台（`testing.py`） |
| `accounts/` | カスタムユーザー（`role`）、Googleログイン、JWT（アクセストークンは応答本文、リフレッシュトークンは httpOnly Cookie）、`IsAdminRole` |
| `agents/` | `AgentConfig` / `PromptTemplate` / `UsageRecord`、LLMラッパー（`llm.py`）、`Agent` クラス（`agent.py`）、使用量の上限（`usage.py`）、初期プロンプト（`seed_prompts/`） |
| `chat/` | `Conversation` / `Message` / `PendingAgentCall`、サービス層（`services.py`）、SSEのメッセージ送信、ボタン操作のAPI |
| `summaries/` | `RequirementSummary`、確定送信とメール（`services.py`）、管理者向けAPI |

実装上の決まりごと:

- **LLMの呼び出しは必ず `agents.agent.Agent` を通す。** 使用量の記録（`UsageRecord`）がここで行われるため、`llm.py` のクライアントを直接呼ぶと上限の計算から漏れる。
- **エージェントは他のエージェントを呼ばない。** エージェントをまたぐ処理は `chat/services.py` の関数が順に `Agent.run()` を呼んで仲介する。
- **内部処理のための入力と出力は `Message` に保存しない。** 依頼者の対話履歴に出さないため。LLMに渡す履歴は常に user / assistant のテキストの並びで、tool use のブロックは保存しない。
- **機械的に解釈する出力は構造化出力（`output_schema`）で受け取る。** スキーマは `chat/services.py` の `CHECK_SCHEMA` / `EXTRACT_SCHEMA` / `SUMMARY_SCHEMA`。
- **LLMを呼ぶAPIは、入口で `ensure_within_limit()` と `conversation_lock()`（または `acquire_lock()`）を通す。**
- ロールプロンプトとテンプレはDBにあり、Djangoの管理サイト（`/django-admin/`）で編集する。`seed_prompts/` は初期値であり、編集しても既存のDBには反映されない。
- エラー応答は `{code, message, ...}` の形に統一している（`config.exceptions.ApiError`）。`message` は依頼者にそのまま見せるため、専門用語を使わない。
- 新しいアプリを追加する際は既存のアプリの構成（`models.py` / `services.py` / `views.py` / `urls.py` / `tests.py`）に倣い、`INSTALLED_APPS` への登録と `config/urls.py` での `include()` を忘れないこと。

## インフラへの申し送り事項

- 管理者リストのファイル（`ADMIN_EMAILS_FILE`）をコードのディレクトリの外（例: `/etc/task-box/admin_emails.txt`）に配置し、アプリから読めるようにする。置き忘れると管理者が誰もいない状態になる。
- `python manage.py purge_conversations` を1日1回定期実行する（保持期間を過ぎた対話履歴の消去）。実行されないと履歴が消えない。
- 「要件の確定」などはLLMを複数回呼ぶため、1リクエストが1分を超えることがある。アプリケーションサーバーとリバースプロキシのタイムアウトは180秒以上にする。
- `POST /api/conversation/messages/` はSSE。リバースプロキシのバッファリングを無効にする（応答に `X-Accel-Buffering: no` を付けている）。
- 同期ワーカーはLLMの応答待ちの間ふさがるため、スレッド型のワーカー（例: gunicorn の gthread）を使う。
- リフレッシュトークンのCookieは `SameSite=Lax`。フロントエンドとAPIは同じ登録ドメインの配下に置く。
- DBは PostgreSQL、メールの送信手段を用意する。
