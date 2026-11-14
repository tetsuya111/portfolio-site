# 要件の確定で、項目の充足判定と要件の抽出を1回のLLM呼び出しにまとめた

対象: タスク6

## 何を

- `backend/chat/services.py`: `CHECK_SCHEMA` / `CHECK_INPUT` / `check_items()` / `EXTRACT_INPUT` を廃止し、`CHECK_EXTRACT_SCHEMA` と `CHECK_EXTRACT_INPUT`、`finalize_summary()` を追加。確定では1回の呼び出しで `complete` / `missing` / `requirements_markdown` を得る。不足があればサマリー作成を呼ばずに打ち切る。
- サマリー作成の呼び出しを `run_summary_agent()` に切り出し、確定の経路では不足項目による差し戻し（422 `summary_incomplete`）を行わず `llm_failed` として扱う。
- `backend/chat/views.py`: `FinalizeView` が `finalize_summary()` を使う。`SummaryDownloadView` と `run_agent()` はプレビュー用の `build_summary()`（従来どおり補完あり）を使う。
- テスト更新: 確定の呼び出し回数（不足あり1回 / 完了2回）を検証。`test_finalize_summary_agent_error` は 502 を期待する形に置き換えた。

## なぜ

同じ「項目がそろっているか」の判定が、確定用のチェックとサマリー作成エージェントの両方で行われ、LLMの費用が二重にかかっていたため。確定1回あたりの呼び出しは3回から2回になった。

## 補足

- APIのレスポンスの形は変えていないため、フロントエンドの変更は不要。
- プレビュー（相場見積もり / 自分見積もり / 現状の要約のDL）の振る舞いと呼び出し回数は変更していない。
