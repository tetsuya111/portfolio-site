---
name: code-review-ocr
description: OpenCodeReview（`npm run ocr`）でgit差分をAIコードレビューする。ユーザーが「コードレビューして」「レビューお願い」「変更を見て」「PR前に確認」など、コードレビュー（code review）を求めたとき、またはコミット・PR作成前に変更を確認する場面では、必ずこのスキルを読み込み、OCRによるレビューをユーザーに提示すること。/code-review-ocr で明示的に起動された場合は即実行する。
---

# OpenCodeReview によるコードレビュー

このリポジトリには `@alibaba-group/open-code-review`（CLI名 `ocr`）が導入されており、`npm run ocr` で起動できる。git差分を設定済みのLLMに送り、レビューコメントを生成する。

## 起動のされ方による分岐

- **ユーザーが `/code-review-ocr` で起動した場合**: 確認せず「実行手順」に進む。引数があればレビュー範囲の指定として解釈する（例: `main`、コミットハッシュ）。
- **コードレビューの依頼から自動で読み込まれた場合**: 実行前に、OCRでレビューできることをユーザーに一言で提示し、実行してよいか確認する。OCRは外部のLLMプロバイダにコード差分を送信し、課金が発生しうるため、無断で実行しないこと。ユーザーが断った場合は通常のレビュー方法に戻る。

## 実行手順

1. **レビュー対象の確認**（LLMを呼ばない）

   ```bash
   npm run ocr -- review --preview
   ```

   対象ファイルが0件なら、その旨を伝えて終了する。

2. **レビュー範囲の決定**（ユーザーの指示がなければ既定の作業ツリー差分）

   | 対象 | コマンド |
   |---|---|
   | 作業ツリーの変更（staged・unstaged・untracked） | `npm run ocr -- review --audience agent` |
   | ブランチ間 | `npm run ocr -- review --from <base> --to <branch> --audience agent` |
   | 特定コミット | `npm run ocr -- review --commit <hash> --audience agent` |

   - プロジェクトルートに `set-ocr-env.bat`（LLM接続用の環境変数を `set` で定義するバッチ。APIキーを含むため `.gitignore` 済み）がある場合は、上記コマンドを次の形で包み、バッチを読み込んでから実行する。
     ```bash
     cmd //c "call $(cygpath -w "$PWD")\\set-ocr-env.bat >nul && npm run ocr -- review --audience agent"
     ```
     - バッチは絶対パスで `call` する（相対パスではcmdから認識されない）。
     - `>nul` は必須。バッチに `@echo off` がないため、省くとAPIキーの行が出力に表示される。
     - バッチの中身を `cat` / Read などで読まないこと（APIキーを含む）。
   - `--audience agent` は進捗表示を省き要約だけを出力する。トークン節約のため必ず付ける。
   - 要件・設計ドキュメントが関連する場合は `--background-file <path>` で背景として渡す。
   - レビューは時間がかかるため、Bashのタイムアウトは長め（例: 600000ms）にする。

3. **結果の提示**

   - 指摘を重要度順にまとめ、該当箇所を `[file:line](path#Lline)` 形式のリンクで示す。
   - 出力をそのまま貼らず、要約して提示する。指摘が0件ならそう明言する。
   - 指摘の妥当性は実際のコードを見て確認し、誤検知と思われるものはその旨を添える。
   - 修正はユーザーの指示があるまで行わない。

## エラー時の対応

- **LLM未設定・認証エラー**: `npx ocr config provider`（対話式）または `npx ocr config set ...` での設定が必要だと伝える。APIキーをClaudeが代わりに入力・表示しないこと。
- **その他のエラー**: エラーメッセージの要点をそのまま伝え、推測で再試行を繰り返さない。
