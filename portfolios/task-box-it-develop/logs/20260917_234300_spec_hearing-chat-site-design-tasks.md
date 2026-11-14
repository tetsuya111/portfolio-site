# hearing-chat-site の design.md と tasks.md を新規作成

## 何を行ったか

- `.kiro/specs/hearing-chat-site/design.md` を新規作成した（ステータス: Draft、未解決事項なし）。
- `.kiro/specs/hearing-chat-site/tasks.md` を新規作成した（19タスク、4マイルストーン）。

## なぜ行ったか

requirements.md の未解決事項がすべて解消されたため、`.kiro/specs/README.md` の進め方に従って設計とタスク分解に進んだ。

## 主な設計判断

- バックエンドは `accounts` / `agents` / `chat` / `summaries` の4アプリ。エージェントはDBの設定から作る薄いクラスとし、エージェント間の受け渡しは常にサービス層が仲介する。
- 機械的に解釈する出力（6項目の判定、要件の抽出、要件サマリー）はすべて Claude の構造化出力で受け取る。メモの「True / OK」の表記揺れと、サマリー作成プロンプト内のエラー形式の矛盾はこれで解消する。
- 入力起点のエージェント呼び出しは tool use で検出し、ツールは実行せずに確認ダイアログへ回す。tool use のブロックは履歴に保存せず、結果をアシスタントのテキストとして残す。
- 対話の応答はSSEでストリーミングする。アクセストークンはメモリ、リフレッシュトークンは httpOnly Cookie。
- 要件サマリーはファイルではなくDBに保存する。下書き（`submitted_at` がnull）→ 条件付き更新で送信済み、とすることで二重送信を防ぐ。
- ロールプロンプトとテンプレの編集は Django の管理サイト、要件サマリーの管理はフロントの管理者画面とする。
- 画面のイメージは、空の `sandbox` とCSPつきの iframe で表示する。見積もりの注意書きはLLMに書かせずフロントが固定で付ける。
- LLMの既定モデルは `claude-opus-5`（環境変数 `LLM_MODEL` で変更可）。現行のClaude APIの仕様（adaptive thinking、`output_config.format`、prefill不可、サンプリング指定不可）は claude-api スキルの資料で確認した。

## 未対応

- 実装は未着手。tasks.md のタスク1から順に進める。
- `.kiro/specs/` 配下の community_sns 由来のspecは残ったまま。
