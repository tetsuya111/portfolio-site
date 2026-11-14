# LINE BOTサーバー（`line_bot/`）

LINE公式アカウントの窓口。Webhookを受けて、ユーザー情報の登録・面談予定日の調整・契約の案内・契約者との対話を行う。仕様は [.kiro/specs/line-bot-server/](../.kiro/specs/line-bot-server/requirements.md)。どの入力に何を返すかの一覧は [line-bot-io.md](line-bot-io.md)。

Djangoの `backend/` とはコードもDBも共有しない独立したアプリで、関わるのはWebのヒアリングサイトへのリンクを案内することだけ。

## セットアップ

```bash
cd line_bot
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env      # 値を埋める
.venv\Scripts\python.exe -m alembic upgrade head
```

CeleryのブローカーにRedisが必要（同梱の `docker-compose.yml` で `docker compose up -d redis`。詳細は [line_bot/README.md](../line_bot/README.md)）。`web` / Celeryの `worker` / Redis の3つがそろっていないと返信は届かない。

開発中のWebhookは ngrok で受ける。`ngrok http 8100` を**アプリより先に**起動し、`.env` に `USE_NGROK=true` を入れておくと、アプリの起動時に公開URLを読み、**LINE DevelopersのWebhookエンドポイントが自動で設定される**（手順は [line_bot/README.md](../line_bot/README.md)）。使う LINE チャネルは **開発用**とし、本番用チャネルとは必ず分ける。

`USE_NGROK=false`（既定・本番）のときは `PUBLIC_BASE_URL` をそのまま公開URLとして使い、LINEのAPIは呼ばない（本番のWebhook設定を上書きしない）。

## コマンド

| コマンド | 内容 |
| --- | --- |
| `python -m uvicorn app.main:app --reload --port 8100` | Webプロセス（Webhookの受信）。本番は `--reload` なし |
| `celery -A app.celery_app worker --loglevel=info --pool=solo` | Celeryのworker（機能の実行・LLM・Pushメッセージの送信）。Redisが必要。Windowsは `--pool=solo`、本番Linuxは `--concurrency=4` |
| `docker compose up -d redis` | ブローカーのRedis（`line_bot/docker-compose.yml`） |
| `python -m app.cli purge` | 保持期間を過ぎた会話履歴（24時間）と処理済みイベント（48時間）を消す。1日1回の定期実行を想定 |
| `python -m app.cli set_contract <userId> <none\|active>` | 契約状態を変更する。**契約状態を変えられるのはこのコマンドだけ** |
| `python -m alembic upgrade head` | マイグレーション |
| `python -m pytest` | テスト。LINE Messaging API とLLMは偽のクライアントに差し替わり、実際のAPIを呼ばない |

## 環境変数

`line_bot/.env` に書く（`.env.example` が雛形）。

| 変数 | 既定値 | 内容 |
| --- | --- | --- |
| `LINE_CHANNEL_SECRET` | なし | Webhookの署名の検証に使う。必須 |
| `LINE_CHANNEL_ACCESS_TOKEN` | なし | メッセージの送信に使う。必須 |
| `LIFF_ID` | なし | LIFFアプリのID。未設定ならテキストのフォーマットで登録を案内する |
| `USE_NGROK` | `false` | **開発用**。`true` のとき、起動時にngrokの公開URLを読み、LINEのWebhookエンドポイントを自動設定する |
| `PUBLIC_BASE_URL` | なし | 公開URL（本番・検証環境用）。`USE_NGROK=false` のときはこの値を使う |
| `NGROK_API_URL` | `http://127.0.0.1:4040/api/tunnels` | ngrokのローカルAPI。ポートを変えている場合に指定する |
| `NGROK_TUNNEL_NAME` | なし | トンネルが複数あるときに名前で選ぶ |
| `ENVIRONMENT` | `development` | `production` かつ `USE_NGROK=true` のときに警告を出す |
| `DATABASE_URL` | sqlite（`line_bot/line_bot.sqlite3`） | 本番は PostgreSQL（`postgresql+psycopg://...`） |
| `REDIS_URL` | `redis://localhost:6379/0` | Celeryのブローカー |
| `ANTHROPIC_API_KEY` | なし | 対話で使う |
| `LLM_MODEL` | `claude-sonnet-5` | |
| `LLM_MAX_TOKENS` | `1000` | LINEの返信は短文のため小さめ |
| `LLM_CLIENT_CLASS` | `app.agents.llm.AnthropicLLMClient` | `app.agents.llm.FakeLLMClient` にすると、APIキーなしで決まった応答を返す |
| `DAILY_LLM_CALL_LIMIT` | `30` | 1ユーザーあたり1日（日本時間）の呼び出し回数の上限 |
| `CONTRACT_PAGE_URL` | なし | 「契約する」で案内するページ。未設定なら「機能改修中」と返す |
| `HEARING_SITE_URL` | なし | Webのヒアリングサイト |
| `HISTORY_RETENTION_HOURS` / `EVENT_RETENTION_HOURS` | `24` / `48` | `purge` が使う保持期間 |
| `HISTORY_MAX_TURNS` | `10` | LLMに渡す直近の往復数。超えた分は保存しない |
| `DIALOGUE_PROMPT_FILE` | `line_bot/prompts/dialogue.md` | 対話プロンプト。**ファイルが無い・空なら仮の応答を返し、LLMを呼ばない** |

## アーキテクチャ

```
LINE → [web: FastAPI] 署名検証 → 重複排除 → 200を即返す（対話は reply で待機メッセージ）
                │ ジョブ登録
                ▼
          [Redis(ブローカー)] → [Celery worker] 機能の実行・LLM → Push メッセージ
                │
          [PostgreSQL] users / conversation_turns / processed_events
```

| ファイル | 役割 |
| --- | --- |
| `app/main.py` | `/webhook`・`/liff`・`/liff/register`・`/healthz` |
| `app/celery_app.py` / `app/tasks.py` | Celeryの設定（`task_acks_late` など）と `handle_event` タスク。Webからは `dispatch()` 経由でのみ渡す |
| `app/public_url.py` / `app/startup.py` | 公開URLの解決（ngrok対応）と、起動時のLINEのWebhookエンドポイントの更新 |
| `app/line/client.py` | 署名の検証、Messaging API のクライアント（reply / push / IDトークンの検証）、クイックリプライ |
| `app/features/router.py` | イベントの振り分け。返信は1通に保つ |
| `app/features/registration.py` | ユーザー情報の登録（テキストとLIFFで共通） |
| `app/features/dialogue.py` | 契約者との対話と会話履歴 |
| `app/agents/` | 対話プロンプトの読み込み、LLMのクライアント、返信の整形 |
| `app/usage.py` | LLM呼び出し回数の上限 |
| `app/retention.py` / `app/cli.py` | `purge` と `set_contract` |

決まりごと:

- Webhookは署名を検証してから処理し、処理の完了を待たずに200を返す。重複は `processed_events` へのINSERTの主キー違反で弾く（SELECT→INSERTにしない）。
- タスクを送れなかったとき（Redisが落ちているなど）は、`processed_events` の記録を消してから500を返す。記録だけ残って二度と処理されない状態を作らないため。
- 機能の判定は postback の `data`（`action=register` など）で行う。メッセージの先頭の文字列では判定しない。例外は登録のフォーマットだけ。
- `userId` は署名を検証したWebhookか、サーバーで検証したLIFFのIDトークンからのみ取得する。リクエストのボディの値は信用しない。
- 待機メッセージは reply（通数を消費しない）、LLMの回答は Push（1通）。対話1往復あたりのPushは1通に保つ。
- 返信は200文字程度のプレーンテキスト。長さ・記号・金額の抑制はプロンプトに任せず、送信前に `app/agents/dialogue.py` で担保する。
- 依頼者向けの文言は `app/messages.py` に集約する。
- 公開URLは `app/public_url.py` が起動時に1回だけ決め、Webhookの設定・LIFFの案内・ログ・`/healthz` がその値を使う。リクエストの処理経路では解決しない。

## 管理者の運用

- **契約状態の変更**: `python -m app.cli set_contract U1234... active`（戻すときは `none`）。ユーザーが未登録だとエラーになるので、先に登録してもらう。Webhookの処理やLIFFの登録からは契約状態を書き換えない。
- **ログに出してよいもの**: `line_user_id`、イベントの種別、機能名、エラーの種類、件数。**出さないもの**: 名前・メールアドレス・メッセージ本文・LLMの入出力。
- 友だち追加時の案内（利用目的・プライバシーポリシー）は、このサーバーではなく LINE Official Account Manager の「あいさつメッセージ」で設定する。
- 管理者が手動で返信する場合は、LINE Official Account Manager でチャットモードに切り替える。

## デプロイ構成

常時起動のプロセスを置ける環境を使う（サーバーレスはコールドスタートの遅延があるため避ける）。必要なのは次の5つ。

| 要素 | 内容 |
| --- | --- |
| `web` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT`。HTTPSの公開URLと `/healthz` |
| `worker` | `celery -A app.celery_app worker --loglevel=info --concurrency=4` |
| PostgreSQL | マネージドのもの |
| Redis | マネージドのもの（Celeryのブローカー専用） |
| cron | `python -m app.cli purge` を1日1回 |

- PaaS（Render / Fly.io / Railway など）なら、この5つをそのまま設定できる。VPSの場合は `web` と `worker` を systemd のユニットに分け、nginx でHTTPSを終端し、`purge` を cron に登録する。
- アプリ内にスケジューラは持たない（プロセスが増えたときに二重実行になるため）。

## インフラへの申し送り事項

- `web` と Celeryの `worker` は別プロセスで常時起動する。`worker` が止まると対話の回答が届かない（タスクはRedisに残るので、再起動すれば再開する）。`/healthz` はworkerの生死を見ないため、`celery -A app.celery_app inspect active` かキューの滞留で確認する。
- Redis と PostgreSQL はマネージドのものを用意する。Redisはジョブキュー専用。
- `python -m app.cli purge` を1日1回定期実行する。実行されないと会話履歴が消えない。
- HTTPSの公開URLが必要（LINEのWebhookはHTTPSのみ）。Webhookのエンドポイントは `POST /webhook`。
- 本番用と開発用でLINEチャネルを分け、それぞれ別のシークレット・トークン・DBを使う。
- 秘密情報（チャネルシークレット、アクセストークン、`ANTHROPIC_API_KEY`）は環境変数で渡し、コミットしない。
- 本番では `USE_NGROK=false` のままにし、`PUBLIC_BASE_URL` にホスティング先のURLを設定する。LINEのWebhookエンドポイントはデプロイ時に人が1回設定する（アプリは書き換えない）。

## 本番公開の前に

- [ ] 対話プロンプト（`prompts/dialogue.md`）が用意されている（空のままだと仮の応答しか返らない）
- [ ] あいさつメッセージに利用目的とプライバシーポリシーを設定した
- [ ] プライバシーポリシーに、LLM（Anthropic）への送信が外国にある第三者への提供に当たりうることを記載した
- [ ] LINE公式アカウントの料金プランを確認した（対話1往復ごとにPushを1通消費する）
- [ ] 開発用チャネルで、友だち追加 → 登録 → 契約者としての対話 → 上限到達までを実機で確認した
