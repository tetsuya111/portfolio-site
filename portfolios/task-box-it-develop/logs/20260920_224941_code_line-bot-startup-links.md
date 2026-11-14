# 起動時に公開URL（ngrok）のリンクを一覧で出すようにした

## 何を

- `app/startup.py` に `setup_logging()` と `show_links()` を追加し、`app/main.py` の lifespan から `setup_logging()` → `configure_public_url()` の順に呼ぶようにした。
- 起動時に次を一覧で出す。日本語のラベルは表示幅（全角=2）で揃える。
  - 公開URL / Webhook URL /（`LIFF_ID` があれば）LIFFのエンドポイント /（ngrok利用時のみ）ngrokの管理画面（`http://127.0.0.1:4040`）
- `app/public_url.py` に `ngrok_inspector_url()` を追加（`NGROK_API_URL` から管理画面のURLを導く）。
- README に実際の出力例を追記。design.md のオブザーバビリティと tasks.md のタスク4にも反映。

## なぜ

公開URLは以前から `logger.info` で出していたが、**uvicornは自分のロガーしか設定せず、アプリのロガーにはハンドラが付かないため、INFOのログが画面に出ていなかった**（WARNING以上だけが既定の最終ハンドラで出る状態）。そのため「起動してもngrokのURLが分からない」状態だった。ログの初期化を入れ、あわせて開発で使うリンクをまとめて出すようにした。

## 確認

- `python -m pytest` 55件パス（新規2件: リンクが出ること、ngrokを使わないときは管理画面を出さないこと）。
- ngrokの応答を差し替えて実行し、出力の体裁（ラベルの揃い）を確認した。
