# set-ocr-env.bat の設定項目を URL / TOKEN / MODEL に変更

## 何を

- `set-ocr-env.bat` の設定項目を `OCR_LLM_URL` / `OCR_LLM_TOKEN` / `OCR_LLM_MODEL` の3つに変更した（`OCR_LLM_PROTOCOL` を削除）。
  - `OCR_LLM_TOKEN` はプレースホルダ値（`your-api-key-here`）とした。
- `.gitignore` に `set-ocr-env.bat` を追加した。

## なぜ

- ユーザーから、設定項目をこの3つにするよう指示があったため。
- バッチにAPIキーを書くことになり、誤ってコミットされるのを防ぐため `.gitignore` で除外した。
