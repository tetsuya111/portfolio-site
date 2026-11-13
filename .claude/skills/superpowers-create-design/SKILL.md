---
name: superpowers-create-design
description: superpowersのbrainstorming・writing-plansを無人実行モードで使い、要件定義（requirements.md）・設計（design.md）・タスク（tasks.md）を確認なしで自動作成する。/superpowers-create-design で起動する。
disable-model-invocation: true
---

# superpowers-create-design

引数（`$ARGUMENTS`）で渡された機能要望・issue本文から、設計ファイル一式を**ユーザーに一度も質問せずに**作成する。

## 無人実行ルール（superpowersの各スキルより優先する）

呼び出すsuperpowersスキルには「ユーザーに質問する」「承認を待つ」「選択肢を提示する」手順がある。このスキルの実行中は、それらをすべて次のように置き換える。

| superpowers側の手順 | このスキルでの扱い |
|---|---|
| 質問して意図を確認する | コード・docs・issueから推定し、最も妥当な案を自分で選ぶ。選んだ根拠を「前提と仮定」節に書く |
| 複数案を提示して選んでもらう | 推奨案を採用し、不採用案は design.md の「検討した代替案」に1行ずつ書く |
| 設計ドキュメントの承認を待つ | 承認を待たず次の工程へ進む |
| 実行方式（subagent/inline）を尋ねる | 尋ねずに終了する（実装はこのスキルの範囲外） |

AskUserQuestion ツールを使わない。応答の途中で「よろしいですか？」「進めてよいですか？」と書かない。ただし下記「必ず確認する操作」は例外。
引数が空でも質問せず、直前の会話・開いているファイル・`memo/` から要望を推定する。推定元もない場合のみ、作成せずに理由を報告して終了する。

## 必ず確認する操作（無人実行ルールの例外）

次の操作は、実行する直前に AskUserQuestion で yes/no を確認し、no なら行わずにその操作なしで続ける。

- このプロジェクト（リポジトリのルート）外のファイルを作成・修正・削除する
- 外部URLにアクセスする（WebFetch・WebSearch・curl など。superpowers公式ドキュメントの参照も含む）

## ファイルの扱い

- 既存ファイルは**読むだけ**。編集・上書き・削除・リネームしない（CLAUDE.md・docs・ソースすべて）。
- 出力先は `docs/specs/<機能名のkebab-case>/` 配下の新規ファイルのみ。同名ディレクトリが既に存在する場合は `-2`、`-3` … を付けた新しいディレクトリを使う。
- superpowers既定の保存先（`docs/superpowers/specs/`・`docs/superpowers/plans/`）は使わない。
- コミットしない（コミットは呼び出し元に任せる）。

## 手順

1. **調査**: CLAUDE.md・`docs/` 配下のベストプラクティス・関連コードを読む。広範囲になる場合は Explore サブエージェントに委譲し、要約だけを受け取る。
2. **requirements.md**: Skill ツールで `superpowers:brainstorming` を読み込み、その考え方（目的・範囲・成功条件の洗い出し）を上記の無人実行ルールで適用する。書式は [docs/requirements-best-practices.md](../../../docs/requirements-best-practices.md) に従う。冒頭に「前提と仮定」節を置く。
3. **design.md**: 同じく brainstorming の設計検討を適用し、[docs/design-doc-best-practices.md](../../../docs/design-doc-best-practices.md) に従って書く。要件IDとの対応を明記する。
4. **tasks.md**: Skill ツールで `superpowers:writing-plans` を読み込み、その粒度（テスト→実装→検証の小さなステップ、対象ファイルパス、確認コマンド）でタスクを書く。各タスクに対応する要件IDを付ける。
5. **自己レビュー**: 3ファイルを読み直し、要件↔設計↔タスクの対応漏れ・矛盾・「TBD」を自分で修正する。
6. **作業ログ**: CLAUDE.md の作業ログ規則に従い `logs/<yyyymmdd_hhMMss>_spec_<機能名>.md` を新規作成する。
7. **報告**: 作成したファイルへのリンクと、「前提と仮定」の要点（ユーザーが後で覆したくなりそうなもの）を箇条書きで示して終了する。
