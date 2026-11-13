# superpowers 統合スキルに「必ず確認する操作」を追加

## 何を

- `superpowers-create-design` と `superpowers-create-from-design-to-pr` の両 SKILL.md に「必ず確認する操作（無人実行ルールの例外）」節を追加した。
- 対象は「プロジェクト外のファイルの作成・修正・削除」と「外部URLへのアクセス」で、実行直前に yes/no 確認を行う。

## なぜ

- `memo/superpower_skill作成.md` に「必ずyes/noのプロンプトを出す状況」が追記されたため。
- ただし `/code-review-ocr`・`git push`・`gh` による PR 作成／コメントはスキル本来の手順として memo に明記されており、毎回確認すると無人実行が成立しないため、起動時点で承認済みとして例外扱いにした。
