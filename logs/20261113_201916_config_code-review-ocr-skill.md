# code-review-ocr スキルの追加

## 何を

- `.claude/skills/code-review-ocr/SKILL.md` を新規作成した。
- `npm run ocr`（OpenCodeReview）で git 差分をレビューする手順をスキル化した。

## なぜ

- `/code-review-ocr` で OCR レビューを起動できるようにするため。
- コードレビューを依頼されたときに、OCR でのレビューを自動でユーザーに提示するため。
- 外部 LLM へ差分を送るため、自動で読み込まれた場合は実行前にユーザーへ確認する設計にした。
