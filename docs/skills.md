# スキル一覧と運用ルール

このリポジトリで定義している Claude Code のプロジェクトスキル（`.claude/skills/` 配下）の索引と、スキルを追加・修正するときのルールをまとめる。各スキルの手順・詳細は各 `SKILL.md` を単一情報源とし、このドキュメントには重複して書かない。

## スキル一覧

| スキル | 用途 | 起動のされ方 |
|---|---|---|
| [code-review-ocr](../.claude/skills/code-review-ocr/SKILL.md) | OpenCodeReview（`npm run ocr`）で git 差分を AI コードレビューする | `/code-review-ocr` で即実行。レビュー依頼から自動で読み込まれた場合は、外部LLMへの送信・課金がありうるため実行前に確認する |
| [security-statics-review-of-trailofbits](../.claude/skills/security-statics-review-of-trailofbits/SKILL.md) | Trail of Bits 製スキル群を組み合わせた、アプリケーションコードの静的セキュリティレビュー | `/security-statics-review-of-trailofbits`、または「セキュリティレビューして」などの依頼で自動 |
| [security-infra-review-of-trailofbits](../.claude/skills/security-infra-review-of-trailofbits/SKILL.md) | CI/CD・Docker・IaC・デプロイ設定・シークレット管理など、インフラ設定のセキュリティレビュー | `/security-infra-review-of-trailofbits`、またはインフラ設定のレビュー依頼で自動 |
| [superpowers-create-design](../.claude/skills/superpowers-create-design/SKILL.md) | superpowers を無人実行モードで使い、`requirements.md`・`design.md`・`tasks.md` を確認なしで作成する | `/superpowers-create-design` で明示起動のみ |
| [superpowers-create-from-design-to-pr](../.claude/skills/superpowers-create-from-design-to-pr/SKILL.md) | 設計→ブランチ作成→TDD実装→テスト・レビュー→修正ループ→push・PR作成までを一気通貫で実行する | `/superpowers-create-from-design-to-pr` で明示起動のみ |

## 使い分け

- **設計だけ作りたい**: `superpowers-create-design`。成果物は `docs/specs/<機能名>/` 配下に作られる（書き方は [requirements-best-practices.md](requirements-best-practices.md)・[design-doc-best-practices.md](design-doc-best-practices.md)）。
- **設計から PR まで任せたい**: `superpowers-create-from-design-to-pr`。作成物は `portfolios/<プロジェクト名>/` 配下に置かれ、途中のレビューは標準の `code-review` を使い、`code-review-ocr` は引数で明示した場合のみ使う。
- **コミット・PR 前の変更確認**: `code-review-ocr`。
- **セキュリティ確認**: アプリケーションコードが中心なら `security-statics-review-of-trailofbits`、CI/CD・コンテナ・IaC などの設定が中心なら `security-infra-review-of-trailofbits`。両者は段階の定義と出力形式（[report-format.md](../.claude/skills/security-statics-review-of-trailofbits/references/report-format.md)）を共用する。

## 前提となる外部プラグイン・ツール

プロジェクトスキルの多くは、ユーザー設定で有効化したプラグインのスキルを呼び出す。セッションに読み込まれていない場合の扱いは各 `SKILL.md` に従う。

| 依存先 | 使うスキル |
|---|---|
| superpowers（`brainstorming`・`writing-plans`・`test-driven-development` など） | `superpowers-create-design`、`superpowers-create-from-design-to-pr` |
| Trail of Bits 製プラグイン（`insecure-defaults`・`sharp-edges`・`supply-chain-risk-auditor`・`static-analysis`・`variant-analysis`・`fp-check`・`agentic-actions-auditor`） | `security-statics-review-of-trailofbits`、`security-infra-review-of-trailofbits` |
| `@alibaba-group/open-code-review`（`npm run ocr`）と LLM プロバイダの認証情報 | `code-review-ocr`、`superpowers-create-from-design-to-pr`（引数でOCRを明示した場合のみ。使えない場合は標準の `code-review` で代替） |
| `gh` CLI（認証済み） | `superpowers-create-from-design-to-pr`（PR作成・PRコメント） |

## スキルの追加・修正ルール

- 配置: `.claude/skills/<スキル名>/SKILL.md`。補助資料は同ディレクトリの `references/` に置き、複数スキルで共用する資料は1か所に置いて参照する。
- スキル名: 英小文字 kebab-case。外部プラグインのスキルを組み合わせるものは、元のプラグイン名がわかる名前にする（例: `*-of-trailofbits`、`superpowers-*`）。
- 記述言語: 本文・frontmatter の `description` ともに日本語で書く。
- `description`: いつ使うか（自動で読み込ませたい依頼の言い回し）と、`/<スキル名>` で起動された場合の挙動を書く。明示起動のみにしたいスキルは、その旨だけを書いて自動読み込みの条件を書かない。
- 確認なしで進める（無人実行の）スキルでも、プロジェクト外のファイル操作・外部への送信・課金が発生する操作など、取り消しにくい操作の扱いを `SKILL.md` に明記する。
- 作成・修正時は `superpowers:writing-skills` の手順に沿って、意図どおり動くか確認する。書き方の一般原則は [prompt-guidelines.md](prompt-guidelines.md) に従う。
- 作業ログ: スキルの新規作成・修正も `logs/` に記録する。種別は新規作成なら `skill`、既存スキルの修正なら `config` を使う（既存ログの命名に合わせる）。
- スキルを追加・削除・用途変更したら、このドキュメントの一覧も更新する。
