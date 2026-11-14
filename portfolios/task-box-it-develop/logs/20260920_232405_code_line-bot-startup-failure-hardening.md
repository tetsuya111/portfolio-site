# 起動時の公開URL設定で、例外が漏れてアプリが起動できなくなる不具合を修正

## 何が起きていたか

`USE_NGROK=true` で起動すると、公開URLの表示までは成功するが、その直後に

```
httpx.LocalProtocolError: Illegal header value b'Bearer '
ERROR:    Application startup failed. Exiting.
```

でアプリが起動できなかった。原因は2つ。

1. `.env` の `LINE_CHANNEL_ACCESS_TOKEN` が空のため、`Authorization: Bearer `（値なし）という不正なヘッダになり、httpx が `LocalProtocolError` を投げた。
2. `app/startup.py` は `LineApiError` しか捕まえておらず、httpx の例外がそのまま lifespan まで伝播した。設計・要件では「どの段階で失敗しても起動を止めない」としていたのに、その担保が `LineApiError` に限定されていた。

## 直したこと

- `app/line/client.py`
  - `_headers()` でアクセストークンが空なら `LineApiError("LINE_CHANNEL_ACCESS_TOKEN が設定されていません")` を投げる（不正なヘッダで通信を試みない）。
  - Webhookエンドポイントの3メソッドを `_call()` にまとめ、httpx の例外を `LineApiError` に包む（呼び出し元は1種類だけ捕まえればよい）。
- `app/startup.py`
  - `configure_public_url()` を薄い包みにして、**想定外の例外もすべて捕まえて警告に落とす**（起動を止めない）。実処理は `_configure_public_url()`。
  - アクセストークンが未設定のときは、Webhookの更新に進まず「手動で設定すべきURL」を警告として出す。
- テスト追加: トークン未設定でも起動が続き更新が行われないこと、クライアントが想定外の例外を投げても起動が止まらないこと。

## 併せて直したテストの問題

テストが開発者の `line_bot/.env`（`USE_NGROK=true`）を拾い、実際に動いている ngrok のURLを取得していた。`tests/conftest.py` の共通設定に `USE_NGROK` / `PUBLIC_BASE_URL` / `NGROK_API_URL` / `NGROK_TUNNEL_NAME` / `ENVIRONMENT` を固定する行を追加した（`backend/` と同じ「ローカルの .env に左右されない」方針）。

## 確認

`python -m pytest` 57件パス（新規2件）。
