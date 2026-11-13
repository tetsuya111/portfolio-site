---
name: security-statics-review-of-trailofbits
description: Trail of Bits製のセキュリティスキル群（insecure-defaults、variant-analysis、sharp-edges、supply-chain-risk-auditor、semgrep、fp-check など）を組み合わせて、コードの静的セキュリティレビューを行う。ユーザーが「セキュリティレビューして」「脆弱性を探して」「安全か確認して」「リリース前にセキュリティチェック」など、アプリケーションコードのセキュリティ観点のレビューを求めたときに使う。/security-statics-review-of-trailofbits で明示的に起動された場合は即実行する。インフラ・CI/CD・コンテナ設定が中心の場合は security-infra-review-of-trailofbits を使う。
---

# Trail of Bits スキルによる静的セキュリティレビュー

`insecure-defaults` を中心に、Trail of Bits のスキルを用途別に組み合わせて静的レビューを行い、`variant-analysis` で類似バグを洗い出す。結果は [references/report-format.md](references/report-format.md) の5段階・出力形式でまとめる。

## 引数

- 引数なし: リポジトリ全体（`.`）を対象にする。
- パス（ファイル・ディレクトリ）: その範囲を対象にする。
- ブランチ名・コミット範囲（例: `main..HEAD`）: その差分を対象にする（手順2で `differential-review` を追加する）。

## 呼び出すスキルとその役割

| 順 | スキル（呼び出し名） | 役割 | 実行する条件 |
|---|---|---|---|
| 1 | `insecure-defaults`（コマンド `/insecure-defaults:audit`） | **中心**。フォールバックの秘密情報、デフォルト認証情報、fail-open、弱い暗号、過剰な許可、デバッグ機能の残置を、候補ごとに追跡してから報告する | 常に |
| 2 | `differential-review:differential-review` | 変更差分の影響範囲（blast radius）とテスト有無の確認 | 引数が差分のとき |
| 3 | `sharp-edges:sharp-edges` | 誤用しやすいAPI・設定スキーマ・危険なデフォルト値の設計 | 常に |
| 4 | `supply-chain-risk-auditor:supply-chain-risk-auditor` | 依存パッケージの既知脆弱性、放棄されたパッケージ、install時スクリプト | `package.json` / lockfile 等の依存定義があるとき |
| 5 | `static-analysis:semgrep` | ルールベースの網羅スキャン | `semgrep` コマンドが使えるとき（スキル側が実行計画の承認を求めるので、ユーザーに確認する） |
| 6 | `variant-analysis:variant-analysis` | 手順1〜5で見つかった指摘ごとに、同じ根本原因の別箇所を探す | 指摘が1件以上あるとき |
| 7 | `fp-check:fp-check` | 要修正・要確認の候補が本当に悪用可能かの検証（誤検知の除外） | 要修正・要確認の候補があるとき |

言語固有のレビュー（C/C++ なら `c-review`、Rust なら `rust-review`、スマートコントラクトなら `building-secure-contracts` 系）は、対象言語が該当するときだけ手順3の後に追加する。

## スキルが使えないときのフォールバック

各スキルのプラグインはユーザー設定（`~/.claude/settings.json`）で有効化済みの想定で、Skill ツール（`insecure-defaults` はスラッシュコマンド）で呼び出す。セッションに読み込まれていない、無効化された、実行に失敗したなどで使えない場合に限り、次の順で代替し、どちらを使ったかを出力の「前提」に書く。

1. **marketplace 上のファイルを直接読んで従う**: `~/.claude/plugins/marketplaces/trailofbits/plugins/<プラグイン名>/skills/<スキル名>/SKILL.md` を Read し、その手順に従って自分で実施する。
2. **`insecure-defaults` の場合**: コマンドは `Workflow` ツールを必要とする。使えないときは `~/.claude/plugins/marketplaces/trailofbits/plugins/insecure-defaults/references/*.md`（6カテゴリ）を読み、各カテゴリの検出パターンを Grep で探し、候補ごとに「値がどこから来て、どのセキュリティ判断に届くか」を追跡してから報告する。追跡できなかった候補は「要確認」にする。
3. ファイル自体も見つからない場合: そのスキルの観点は「その他」に「未実施（理由）」として記録し、インストール方法（`/plugin install <プラグイン名>@trailofbits`）を備考に書く。勝手にインストールしない。

## 手順

1. **前提の確定**: 対象範囲、言語・フレームワーク、依存定義の有無、公開範囲（外部公開か、社内向けか）を確認する。脅威モデルを推測した場合はその旨を記録する。
2. **スキルの実行**: 上の表の順に、条件を満たすものを実行する。調査が広範囲になる場合は、スキルごとにサブエージェントに委譲し、指摘の一覧（場所・内容・根拠）だけを受け取る。
3. **類似バグの探索**: 指摘ごとに `variant-analysis` を実行し、根本原因が同じ箇所を元の指摘に紐付ける。
4. **検証**: 要修正・要確認の候補を `fp-check` で検証し、誤検知は「その他」に移して除外理由を書く。
5. **段階付けと統合**: 複数のスキルが同じ箇所を指摘した場合は1件に統合し、検出元を併記する。[references/report-format.md](references/report-format.md) の基準で段階を付ける。
6. **出力**: [references/report-format.md](references/report-format.md) の出力形式（前提 → 概要 → 段階 → 備考 → まとめ）で出力する。

## よくある間違い

| 間違い | 正しい対応 |
|---|---|
| パターンにマッチしただけで要修正にする | 値の出どころと到達先を追跡してから段階を決める。追跡できなければ要確認 |
| 類似バグを独立した指摘として件数に数える | 元の指摘の直下に `類似バグ` として列挙する |
| スキルが動かなかったことを書かずに「問題なし」とする | 実行結果を「前提」に、未実施の観点を「その他」と「備考」に書く |
| 該当なしの段階の見出しを省く | 見出しを残して「該当なし」と書く |
| インフラ設定（Dockerfile、GitHub Actions、IaC）を深掘りする | このスキルでは触れる程度にとどめ、`security-infra-review-of-trailofbits` を案内する |
