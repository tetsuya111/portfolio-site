---
name: security-infra-review-of-trailofbits
description: Trail of Bits製のセキュリティスキル群（agentic-actions-auditor、insecure-defaults、supply-chain-risk-auditor、sharp-edges、semgrep、variant-analysis など）を組み合わせて、インフラ設定のセキュリティレビューを行う。GitHub Actions などのCI/CDワークフロー、Dockerfile・docker-compose、devcontainer、IaC（Terraform など）、ホスティング・デプロイ設定（vercel.json、netlify.toml、nginx 等）、環境変数・シークレット管理のレビューを求められたときに使う。/security-infra-review-of-trailofbits で明示的に起動された場合は即実行する。アプリケーションコードが中心の場合は security-statics-review-of-trailofbits を使う。
---

# Trail of Bits スキルによるインフラ設定セキュリティレビュー

`security-statics-review-of-trailofbits` と同じ進め方で、対象をインフラ設定に絞って重点的にレビューする。段階の定義と出力形式は [../security-statics-review-of-trailofbits/references/report-format.md](../security-statics-review-of-trailofbits/references/report-format.md) に従い、スキルが使えないときのフォールバックは [../security-statics-review-of-trailofbits/SKILL.md](../security-statics-review-of-trailofbits/SKILL.md) の「スキルが使えないときのフォールバック」に従う。

## 引数

- 引数なし: リポジトリ内のインフラ設定ファイル全体を対象にする。
- パス・差分の指定: 静的レビューと同じ扱い。

## 対象ファイルの洗い出し

最初に Glob で次を探し、見つかったものだけを対象として「前提」に列挙する。

| 区分 | 主なファイル |
|---|---|
| CI/CD | `.github/workflows/*.yml`, `.github/actions/**/action.yml`, `.gitlab-ci.yml` |
| コンテナ | `Dockerfile*`, `docker-compose*.yml`, `.dockerignore`, `.devcontainer/**` |
| IaC | `*.tf`, `*.tfvars`, `cdk.json`, Kubernetes マニフェスト, Helm チャート |
| ホスティング・配信 | `vercel.json`, `netlify.toml`, `firebase.json`, `nginx.conf`, `_headers`, `_redirects` |
| 環境変数・シークレット | `.env*`, `.gitignore`（`.env` 等の除外漏れ）, フレームワークの公開用環境変数（`NEXT_PUBLIC_*`, `VITE_*` 等） |
| 依存・ビルド | `package.json` の scripts, lockfile, `.npmrc` |

## 呼び出すスキルとその役割

| 順 | スキル（呼び出し名） | 重点観点 | 実行する条件 |
|---|---|---|---|
| 1 | `agentic-actions-auditor:agentic-actions-auditor` | AIエージェントを呼ぶワークフローへのプロンプトインジェクション | ワークフローがある場合は常に |
| 2 | `insecure-defaults`（コマンド `/insecure-defaults:audit <設定ファイルのパス>`） | **中心**。設定ファイル上のデフォルト認証情報、過剰な許可（CORS `*`、`0.0.0.0` バインド、公開バケット）、デバッグ有効、fail-open | 常に |
| 3 | `supply-chain-risk-auditor:supply-chain-risk-auditor` | 依存・install時スクリプト・ベースイメージやActionの出どころ | 依存定義やワークフローがあるとき |
| 4 | `sharp-edges:sharp-edges` | 一箇所の変更で危険になる設定（環境ごとの差分、上書き可能なデフォルト） | 常に |
| 5 | `static-analysis:semgrep` | IaC・Dockerfile・GitHub Actions 向けルールセットでのスキャン | `semgrep` が使えるとき（実行計画をユーザーに確認） |
| 6 | `variant-analysis:variant-analysis` | 同じ設定ミスが他のワークフロー・環境・ステージにないか | 指摘が1件以上あるとき |
| 7 | `fp-check:fp-check` | 要修正・要確認の候補の検証 | 要修正・要確認の候補があるとき |

## スキルの観点に加えて必ず確認する項目

スキルの検出範囲外になりやすいため、手順の中で直接確認する。

- **GitHub Actions**: `permissions:` の未指定・`write-all`、`pull_request_target` / `workflow_run` での未信頼コードのチェックアウト、`${{ github.event.* }}` の `run:` への直接埋め込み、サードパーティ Action のコミットSHA固定の有無、`secrets` の fork PR への露出。
- **コンテナ**: root 実行（`USER` 未指定）、`latest` タグ、`ADD` によるリモート取得、ビルド引数・レイヤーへの秘密情報の混入、`.dockerignore` からの `.env` / `.git` の除外漏れ。
- **ホスティング・配信**: セキュリティヘッダー（CSP、HSTS、`X-Content-Type-Options`、`frame-ancestors`）、リダイレクトのオープンリダイレクト、プレビュー環境の公開範囲。
- **シークレット**: リポジトリに入った `.env`・鍵ファイル、クライアントに公開される環境変数への秘密情報の混入。

## 手順

1. **対象ファイルの洗い出し**（上表）と前提の確定。対象が1件もなければ、その旨を出力して終了する。
2. **スキルの実行**: 上の表の順に条件を満たすものを実行する。ファイル区分ごとにサブエージェントに委譲してよい。
3. **必須確認項目のチェック**: 上の「必ず確認する項目」を直接確認する。
4. **類似バグの探索**（`variant-analysis`）→ **検証**（`fp-check`）→ **段階付けと統合**: 静的レビューと同じ。
5. **出力**: 共通の出力形式で出力する。見出しは `# セキュリティレビュー結果（インフラ）` とし、「前提」に洗い出した対象ファイルの一覧を含める。

## よくある間違い

| 間違い | 正しい対応 |
|---|---|
| 本番の設定値を見ずに「要修正」と断定する | リポジトリ外の設定（ホスティングの管理画面、リポジトリ設定、Secrets）に依存する場合は要確認にし、確認先を書く |
| ワークフローの1ファイルだけ見て終える | `variant-analysis` で他のワークフロー・ジョブ・環境に同じ設定がないか確認する |
| アプリケーションコードの脆弱性を深掘りする | 触れる程度にとどめ、`security-statics-review-of-trailofbits` を案内する |
