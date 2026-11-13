# OCR用環境変数設定バッチの作成

## 何を

- `set-ocr-env.bat` をプロジェクトルートに作成した。
  - `OCR_LLM_URL` / `OCR_LLM_MODEL` / `OCR_LLM_PROTOCOL` / `OCR_LLM_TOKEN` を `setx` でユーザー環境変数に保存する。
  - URL・モデル・プロトコルはバッチ内に記述し、APIトークンは実行時に入力させる（ファイルには保存しない）。

## なぜ

- `npm run ocr` でのレビューにはLLM接続先の設定が必要だが、`.opencodereview/config.json` はホームディレクトリ（`~/.opencodereview/`）からしか読まれず、プロジェクトルートに置いても読まれないことを検証で確認したため。
- トークンをリポジトリに残さないよう、ファイルには書かず実行時入力とした。
- `setx` で永続化することで、npmスクリプトやClaude Codeから起動するプロセスからも参照できるようにした。
