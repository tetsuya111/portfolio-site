# Hooks（イベント駆動の自動化）

KiroのAgent Hooksに相当する「特定のイベントで自動的にエージェントの作業を走らせる」仕組みを、Claude Code本来のhooks機構（`.claude/settings.json` の `hooks` 設定）で実装する。設定の実体は `.claude/settings.json` に一本化し、ここには「何が・いつ・なぜ」動くかの一覧だけを記載する（設定内容そのものを重複して書かない）。

## 現在設定されているhooks

| イベント | 対象 | 動作 | 目的 |
| --- | --- | --- | --- |
| PostToolUse (Edit/Write) | `frontend/**/*.{ts,tsx,js,jsx}` | 編集したファイルに `eslint --fix` を実行 | 保存のたびに手動でlintを走らせなくても、スタイル上の問題を自動修正する |

新しいhookを追加・変更する場合は `.claude/settings.json` を更新し、このテーブルも合わせて更新すること。
