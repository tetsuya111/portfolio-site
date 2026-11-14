# LINE BOTの公開URLの自動設定（ngrok対応）の design.md / tasks.md を作成

## 何を

`.kiro/specs/line-bot-public-url/` に design.md と tasks.md を新規作成し、requirements.md の未解決事項4件を確定させた（ベストプラクティスに従う方針）。

- design.md: 公開URLを決める責務を `app/public_url.py` に集約し、起動時（FastAPIのlifespan）に1回だけ解決する。`USE_NGROK=true` のときだけ、ngrokのローカルAPIからURLを読み、LINEのWebhookエンドポイントを更新して疎通確認する。
- tasks.md: 5タスク（設定と解決 → ngrok取得 → LINEのWebhook更新 → 起動フックと安全装置 → ドキュメント）。

## 確定した未解決事項

| 事項 | 決定 | 理由 |
| --- | --- | --- |
| ngrokの起動主体 | 開発者が別ターミナルで `ngrok http 8100` を起動し、アプリは `http://127.0.0.1:4040/api/tunnels` から読むだけ。アプリはトンネルを張らない | アプリがトンネルを張ると `uvicorn --reload` のたびにURLが変わり、LINEのAPIを無駄に叩くうえ設定が安定しない。本番に不要な依存とコードを持ち込まずに済む |
| LIFFエンドポイントの自動更新 | 行わない。起動ログで設定すべきURLを案内する | LIFF更新APIは権限が別で、誤って本番のLIFFを書き換えたときの影響が大きい。現状LIFFは未使用 |
| `--reload` での更新頻度 | 現在値（`GET`）と比較し、異なるときだけ `PUT` する | トンネルがアプリと独立しているためURLが変わらず、実質1回で済む |
| 検証環境の扱い | ngrokは使わず `USE_NGROK=false` + `PUBLIC_BASE_URL` | 常設環境に一時的なトンネルを使う理由がない |

## 設計で決めたこと

- 設定は5つ（`USE_NGROK` / `PUBLIC_BASE_URL` / `NGROK_API_URL` / `NGROK_TUNNEL_NAME` / `ENVIRONMENT`）。既定は `USE_NGROK=false` で、入れない限り現在の挙動は変わらない。
- **ngrokの認証トークンをアプリが持たない**（`ngrok config add-authtoken` でngrok側に設定）。これに合わせて requirements.md の ストーリー1 基準7 を「アプリで保持しない」に更新した。
- `USE_NGROK=false` のときはLINEのAPIを一切呼ばない（本番のWebhook設定を上書きしない）。`ENVIRONMENT=production` との併用は警告。
- 失敗しても起動を止めない（ngrok 3秒 / LINE 10秒のタイムアウト、手作業用のURLをログに出す）。
- `/healthz` に `public_url` と `ngrok` を出し、`ok` の判定には含めない。

## 補足

実装は未着手。DoDには「実際に `ngrok http 8100` を起動してWebhookの自動更新とメッセージ受信を確認する」を残している。
