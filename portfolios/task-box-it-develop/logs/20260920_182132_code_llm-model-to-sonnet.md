# 既定のLLMモデルを claude-opus-5 から claude-sonnet-5 に変更

## 何を

バックエンドが呼び出すLLMの既定のモデルを Sonnet 5 に変更した。変更したファイルは次の6つ。

- `backend/config/settings.py` — `LLM_MODEL` の既定値
- `backend/.env.example` / `backend/.env` — ローカルの設定値（`.env` はコミット対象外）
- `docs/backend.md` — 環境変数の表
- `.kiro/steering/tech.md` — 技術選定の記載
- `.kiro/specs/hearing-chat-site/design.md` — LLMクライアントの記載（既定値）と、リスク表の「既定のモデルでは費用が想定より高い」の行（モデル名を書かない表現に変更）

`.kiro/specs/hearing-chat-site/tasks.md` の完了済みチェックリストは、当時の実施内容の記録のため変更していない。

## なぜ

ユーザーの指示による。LLMの費用を抑えるため。モデルは環境変数 `LLM_MODEL` で切り替えられるため、必要なら元に戻せる。

## 確認

- `python manage.py test` — 45件すべてパス（テストは偽のLLMクライアントに差し替えるため、モデルの変更の影響を受けない）。
- 実際のLLMを使った動作確認（ヒアリング・見積もり・要件サマリーの品質）は未実施。費用がかかるため、ユーザーの了承を得てから行う。Opus 5 からの変更で出力の質が変わる可能性があるため、プロンプトの調整が必要になるかもしれない。
