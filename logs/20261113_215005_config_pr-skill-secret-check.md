# superpowers-create-from-design-to-pr に push 前の秘密情報チェックを追加

## 何を

- `.claude/skills/superpowers-create-from-design-to-pr/SKILL.md` の「6. 完了処理」の先頭に、手順0「秘密情報チェック」を追加した。
  - 差分に秘密情報らしいファイル名や値があれば、push せずに停止して報告する。報告には値を書かず、ファイル名と行番号だけを示す。

## なぜ

- セキュリティレビュー（W-3）で、このスキルが無人実行で `git push` / PR作成を事前承認しており、秘密情報が確認なしで外部に出うると指摘されたため。
