# code-review-ocr スキルに環境変数バッチの読み込み手順を追記

## 何を

- `.claude/skills/code-review-ocr/SKILL.md` の実行手順に、`set-ocr-env.bat` がある場合は `cmd //c "call <絶対パス>\set-ocr-env.bat >nul && npm run ocr ..."` の形でバッチを読み込んでからOCRを実行する手順を追記した。
  - 絶対パスで `call` すること、`>nul` でAPIキーの表示を防ぐこと、バッチの中身を読まないことを注意点として記載した。

## なぜ

- `set-ocr-env.bat` は `set` で環境変数を定義するため、Claude Code のシェルには引き継がれず、そのままでは `npm run ocr` がLLM未設定エラーになったため。
- 検証の結果、相対パスではcmdからバッチが認識されず、絶対パスで `call` すると読み込めることを確認したため、その形で記載した。
