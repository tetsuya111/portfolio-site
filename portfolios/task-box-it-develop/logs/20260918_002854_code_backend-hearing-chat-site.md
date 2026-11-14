# バックエンド（hearing-chat-site タスク1, 3, 4, 6〜15）を実装

## 何を行ったか

- `backend/` に Django + DRF のプロジェクトを新規作成した（`config` と、`accounts` / `agents` / `chat` / `summaries` の4アプリ）。
- Googleログイン + JWT、エージェント設定とテンプレ、LLMラッパーと `Agent` クラス、1日ごとの使用量の上限、対話（SSE）、入力起点のエージェント呼び出しの検出と許可、要件サマリーの作成、ボタン操作のAPI、確定送信とメール、管理者向けAPIを実装した。
- 初期プロンプトを `memo/` から `backend/agents/seed_prompts/` にコピーし、`seed_agents` / `set_admin` コマンドを追加した。`summary.md` は出力の入れ物を構造化出力に合わせて差し替え、`hearing.md` は末尾に「他のエージェントの呼び出し」「システムからの依頼」の節を追記した（`memo/` の原本は変更していない）。
- 開発用ログイン（`ALLOW_DEV_LOGIN`）とデモ用のLLMクライアント（`agents.demo.DemoLLMClient`）を追加した。どちらも既定は無効。

## なぜ行ったか

`.kiro/specs/hearing-chat-site/tasks.md` の実装。開発用ログインとデモLLMは、GoogleのクライアントIDとAPIキーが未準備でも画面と流れを確認できるようにするため。

## 確認したこと

- `python manage.py test`: 45件すべて成功（LLMは偽のクライアント）。
- デモLLMでのHTTPの通し確認: ログイン → SSEの逐次受信 → 確認ダイアログ → 見積もり → 確定（不足あり / なし）→ 二重送信なし → 管理者の一覧・対応状況の変更 → Cookieでのトークン再発行。

## 未確認

- `AnthropicLLMClient` は実際のAPIでは未実行（APIキーが未設定）。
- 実際のGoogleログインは未確認（クライアントIDが未設定。検証処理はモックでテスト）。

## 注意

- 同じPCで community_sns の開発サーバーが 8000 / 3000 番を使用中だった。Windowsでは同じポートで二重に起動でき、別プロジェクトの応答が返ってきたため、ローカルの確認は 8001 / 3001 番で行った（`backend/.env` と `frontend/.env.local`。どちらもコミット対象外）。community_sns のプロセスには触れていない。
