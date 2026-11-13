superpower用のスキルを作成
# 概要
superpowerのスキルを統合的に呼び出せるスキルを作成したい。
呼びだすスキルは用途に応じてベストプラクティスや公式ドキュメントに従い任意で選定し作成する。

# 公式ドキュメント
https://github.com/obra/superpowers

# /superpowers-create-design
## 要件
- 要件定義ファイル、デザイン、タスクなどの設計ファイルを自動で作成する
- 既存のファイルは読みとるだけ
- yes/noのプロンプトを出力しない

# /superpowers-create-from-design-to-pr
- /superpowers-create-designに従い設計ファイルを作成する
- yes/noのプロンプトを出力しない
- 既存のファイルを修正する前に、ブランチを変更する
    - ブランチ名 : `dev/feature/claude-superpowers/<修正内容の要約>`
- ファイルを修正する
- レビュー時は`/code-review-ocr`を使用する
- テストとレビューにより修正点を発見する
- 実装、修正点の発見、修正を繰り返す
## github連携している場合
- 修正が完了したら、git‘にpushし`gh`コマンドでPRを作成
- 作成したPRにレビューをコメントする

## 注意
### 必ずyes/noのプロンプトを出す状況
- このプロジェクト以外のファイルを修正するとき
- 外部のURLにアクセスするとき