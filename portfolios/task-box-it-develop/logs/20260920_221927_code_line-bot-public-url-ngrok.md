# LINE BOTの公開URLの自動設定（ngrok対応）を実装（タスク1〜5）

## 何を

- `app/config.py`: `USE_NGROK`（既定 false）、`PUBLIC_BASE_URL`、`NGROK_API_URL`、`NGROK_TUNNEL_NAME`、`ENVIRONMENT`（既定 development）を追加。真偽値を読む `_bool()` も追加。
- `app/public_url.py`（新規）: 公開URLを決める唯一の場所。`normalize()` / `from_ngrok()` / `resolve()` / `current()` / `webhook_url()` / `liff_endpoint_url()`。ngrokのローカルAPI（既定 `http://127.0.0.1:4040/api/tunnels`、タイムアウト3秒）から https のトンネルを選び、失敗時は警告を出して `PUBLIC_BASE_URL` にフォールバックする。HTTPS以外は警告。
- `app/line/client.py`: `get_webhook_endpoint()` / `set_webhook_endpoint()` / `test_webhook_endpoint()` を追加。`FakeLineClient` にも同じメソッドを足し、呼び出しを記録できるようにした。
- `app/startup.py`（新規）: `configure_public_url()`。`USE_NGROK=false` ならLINEのAPIを一切呼ばない。true のときは、現在のエンドポイントと比較して**異なるときだけ** `PUT` し、続けて疎通確認を行う。どこで失敗しても例外を外に出さず、手作業用のURLをログに出す。`ENVIRONMENT=production` との併用は警告。`LIFF_ID` があればLIFFに設定すべきURLを案内。
- `app/main.py`: FastAPIの lifespan から `configure_public_url()` を呼ぶ。`/healthz` に `public_url` と `ngrok` を追加（`ok` の判定には含めない）。
- `.env.example` / `line_bot/README.md` / `docs/line-bot.md`: 5つの変数、ngrokの手順（先に起動する、認証トークンはngrok側に設定）、開発用チャネルのトークンだけを置く注意、起動し忘れたときの挙動を記載。

## なぜ

ngrokのURLが起動のたびに変わり、LINE Developers の画面での貼り替えが毎回発生していた。貼り忘れると無反応になるのに気づきにくい。`.kiro/specs/line-bot-public-url/` のタスク1〜5。

## 確認

- `python -m pytest` 53件パス（新規17件）。ngrokのローカルAPIとLINE Messaging API は差し替えており、実際には呼んでいない。
- 検証した挙動: `USE_NGROK=false` ではngrokのAPIもLINEのAPIも呼ばない / トンネルの名前指定 / httpsが無い場合 / 接続失敗時のフォールバック / HTTPSでない場合の警告 / 同じURLなら `PUT` しない / 更新失敗でも起動が続く / 疎通確認の失敗がログに出る / production警告 / LIFFの案内 / `/healthz` の表示。
- lifespanを通した状態で `/healthz` が `public_url` を返すことを実機のプロセスで確認。

## 残っていること

実際に `ngrok http 8100` を起動し、開発用チャネルでWebhookエンドポイントが自動更新されてメッセージが届くところまでの確認（ngrokのアカウントと開発用チャネルが必要）。
