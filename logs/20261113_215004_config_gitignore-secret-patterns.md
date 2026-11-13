# .gitignore に秘密情報ファイルのパターンを追加

## 何を

- `.gitignore` の「環境変数・秘密情報」に `*.p12` / `*.pfx` / `*.jks` / `*.keystore` / `id_rsa*` / `id_ed25519*` / `.npmrc` / `.yarnrc.yml` / `credentials*.json` / `service-account*.json` / `secrets.*` / `*.secret` を追加した。

## なぜ

- セキュリティレビュー（W-2）で、除外が `.env*` / `*.pem` / `*.key` だけだったと指摘されたため。
- OCR は ignore されていない untracked ファイルも外部LLMに送る（`ocr review --preview` で確認）ので、コミットとLLM送信の両方の経路を狭める必要があった。
