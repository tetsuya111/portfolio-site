# ポートフォリオサイト

フリーランスエンジニアのポートフォリオサイトです。自己紹介・経歴、ポートフォリオ、記事をすべて md ファイルで管理し、Astro で静的サイトとしてビルドして、AWS（S3 + CloudFront）で配信します。

- フロントエンド: [Astro](https://astro.build/)（静的出力）+ [Tailwind CSS](https://tailwindcss.com/) v4
- 配信: S3（非公開）+ CloudFront（OAC）+ ACM + Route 53
- CI/CD: CodeBuild（GitHub と連携。PR でテスト、`main` への push でデプロイ）

## 必要なもの

- Node.js 22.23.4 以上（Astro 7 の要件）
- AWS へデプロイする場合: AWS CLI、Route 53 のホストゾーン、GitHub リポジトリ

## ディレクトリ構成

```
portfolio-site/
├── src/
│   ├── content/
│   │   ├── profile/profile.md     # 自己紹介・経歴（1ファイル）
│   │   ├── portfolios/*.md        # ポートフォリオ（1件1ファイル）
│   │   └── articles/*.md          # 記事（1件1ファイル）
│   ├── content.config.ts          # コレクション定義（frontmatter の検証）
│   ├── pages/                     # 公開ページ
│   ├── components/ layouts/ styles/
│   ├── admin/                     # 管理画面（npm run dev のときだけ表示）
│   └── lib/                       # スキーマ・md の読み書き・保存 API の処理
├── integrations/local-admin.ts    # 管理画面と保存 API を開発サーバーにだけ追加する
├── scripts/new-portfolio.mjs      # ポートフォリオ追加コマンド
├── infra/template.yaml            # CloudFormation テンプレート
├── buildspec.yml                  # CodeBuild の設定
└── tests/                         # vitest
```

## ローカルで動かす

```bash
cd portfolio-site
npm install
npm run dev        # http://localhost:4321/ （管理画面は http://localhost:4321/admin/ ）
```

| コマンド | 内容 |
|---|---|
| `npm run dev` | 開発サーバー（管理画面あり） |
| `npm run build` | `dist/` に静的サイトを出力（管理画面は含まれない） |
| `npm run preview` | ビルド結果の確認 |
| `npm test` | 単体テスト |
| `npm run test:build` | ビルドしてから、生成された HTML を検証する |
| `npm run lint` | ESLint と型チェック（`astro check`） |
| `npm run portfolio:new` | ポートフォリオを追加する（下記） |

## コンテンツの更新

どの方法でも md ファイルが更新されるだけなので、公開するには変更をコミットして `main` に push します（CodeBuild がデプロイします）。

### 自己紹介・経歴

`src/content/profile/profile.md` を編集します。frontmatter の `name`（氏名）と `role`（肩書き）は必須です。

```markdown
---
name: 山田 太郎
role: フリーランス Web エンジニア
summary: トップページに表示する一言紹介（任意）
links:                      # 任意
  - label: GitHub
    url: https://github.com/xxxx
---

## 経歴
...
```

`npm run dev` 中は、管理画面の「自己紹介を編集」（`/admin/profile/`）からも編集・保存できます。

### ポートフォリオ

コマンドで追加します（サイト上からは追加できません）。

```bash
npm run portfolio:new -- --slug my-app --title "My App" --tags "Astro,AWS" --url https://example.com
```

- `--slug`（必須）: URL とファイル名になる名前。英小文字・数字・ハイフンのみ、64文字まで。日本語のタイトルからは自動で作らないので必ず指定する
- `--title`（必須）、`--tags`（任意・カンマ区切り）、`--url`（任意・http/https のみ。指定するとタイルに「ポートフォリオのURL」ボタンが出る）

`src/content/portfolios/<スラッグ>.md` が作られるので、`## 概要` 以下に内容を書きます。同じスラッグが既にある場合は何も作らずにエラーになります。

### 記事

`src/content/articles/` に md ファイルを置くだけで追加されます（ファイル名がスラッグになります）。

```markdown
---
title: 記事のタイトル
date: 2026-11-13
tags: [Astro]          # 任意
description: 一覧に出す説明（任意）
draft: false           # true にすると公開ビルドに含めない
---

本文
```

`npm run dev` 中は、管理画面の「記事を追加」（`/admin/articles/new/`）から、フォーム入力または md ファイルのアップロードでも追加できます。既存の記事と同じスラッグでは保存できません（上書きしない）。

### 管理画面について

- 管理画面と保存 API（`/__admin/api/*`）は `npm run dev` のときだけ有効で、`npm run build` の成果物には含まれません。
- 開発サーバーは localhost でだけ待ち受けます。`--host` を付けて外部に公開しないでください。
- 別のサイトのページからの保存（Origin 不一致）、JSON 以外の送信、1 MB を超える送信は拒否します。

## AWS への構築

### 前提

1. Route 53 に、サイトのドメインを管理するホストゾーンがあること。
2. CodeBuild に GitHub の認証情報を登録してあること（コンソールの CodeBuild →「ソースプロバイダーに接続」、または `aws codebuild import-source-credentials --server-type GITHUB --auth-type PERSONAL_ACCESS_TOKEN --token <トークン>`）。トークンはリポジトリに置かないこと。

### スタックの作成

CloudFront で使う ACM 証明書は us-east-1 でしか作れないため、**必ず us-east-1 に**作成します（テンプレートでも他のリージョンを拒否します）。

```bash
aws cloudformation validate-template --region us-east-1 --template-body file://infra/template.yaml

aws cloudformation deploy \
  --region us-east-1 \
  --stack-name portfolio-site \
  --template-file infra/template.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    DomainName=portfolio.example.com \
    HostedZoneId=Z0123456789ABCDEFGHIJ \
    GitHubRepoUrl=https://github.com/<owner>/<repo>.git \
    DeployBranch=main
```

作成されるもの:

| リソース | 内容 |
|---|---|
| S3 バケット | サイトのファイル置き場。公開せず、CloudFront からだけ読める |
| CloudFront | HTTPS（TLS 1.2 以上）で配信。`/about/` → `/about/index.html` の補完、404 ページ、セキュリティヘッダー |
| ACM 証明書 | DNS 検証（検証用レコードはホストゾーンに自動作成） |
| Route 53 | ドメイン → CloudFront の A / AAAA レコード |
| CodeBuild | GitHub Webhook。権限はログ出力・バケットへの同期・キャッシュ無効化のみ |

証明書の検証が終わるまで、スタックの作成には数分〜数十分かかります。

### CI / デプロイの流れ

- `portfolio-site/` 配下を変更するプルリクエストを作成・更新すると、CodeBuild が `npm test` → `npm run lint` → `npm run build` を実行し、結果を GitHub に表示します。
- `DeployBranch`（既定 `main`）に push されると同じ処理を行い、成功した場合だけ `dist/` を S3 に同期（`--delete`）して CloudFront のキャッシュを無効化します。
- 初回は、スタック作成後に `main` へ push するか、CodeBuild のコンソールからビルドを開始してください（手動開始ではデプロイされないため、初回デプロイは push で行います）。
