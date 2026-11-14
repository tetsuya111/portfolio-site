---
title: このポートフォリオサイト
tags:
  - Astro
  - TypeScript
  - Tailwind CSS
  - Zod
  - Vitest
  - Playwright
  - axe-core
  - ESLint
  - Node.js
  - AWS
  - Amazon S3
  - Amazon CloudFront
  - CloudFront Functions
  - AWS WAF
  - AWS Certificate Manager
  - Amazon Route 53
  - AWS CloudFormation
  - AWS CodeBuild
  - Amazon CloudWatch Logs
  - AWS Budgets
  - GitHub
  - Claude Code
url: /
date: 2026-11-13
---

## 概要

自己紹介・ポートフォリオ・記事をまとめて公開している、このサイトそのものです。コンテンツはすべて Markdown ファイルで管理し、Astro でビルドした静的 HTML を S3 + CloudFront から配信しています。インフラは CloudFormation のテンプレート1つで構築し、CodeBuild による CI/CD でテストからデプロイまでを自動化しています。

## 主な機能

| 機能 | 内容 |
| --- | --- |
| トップページ | 氏名・肩書き・一言紹介、ポートフォリオのタイル一覧、最新記事3件 |
| 自己紹介 | 経歴などを `profile.md` の本文から表示 |
| ポートフォリオ | 一覧（タイル表示）と詳細ページ。タグ・URL ボタン付き |
| 記事 | 新しい順の一覧と詳細ページ。`draft: true` の下書きはページ自体を生成しない |
| 管理画面 | 開発サーバー上だけで動く、自己紹介の編集・記事の追加画面（本番ビルドには含めない） |
| ポートフォリオ追加コマンド | `npm run portfolio:new` で md を作成 |
| 取り込んだアプリの配信 | 他のプロジェクトのフロントエンドをビルドし、`/apps/<スラッグ>/` で同じドメインから配信 |

## 技術スタック

| 分類 | 技術 |
| --- | --- |
| フレームワーク | Astro（静的出力・コンテンツコレクション・ファイルベースルーティング）、自作の Astro インテグレーション |
| 言語 | TypeScript（strict）、Node.js |
| スタイル | Tailwind CSS v4（Vite プラグイン）、@tailwindcss/typography |
| スキーマ・検証 | Zod（frontmatter のスキーマをビルド時と保存時で共用）、YAML |
| テスト | Vitest（単体テスト・ビルド成果物のテスト・インフラ定義のテスト）、Playwright（E2E）、axe-core（WCAG 2.1 A/AA のアクセシビリティ検査） |
| 静的解析 | ESLint（typescript-eslint・eslint-plugin-astro）、astro check |
| 配信 | Amazon S3（非公開バケット）、Amazon CloudFront（OAC・HTTP/2・HTTP/3・IPv6）、CloudFront Functions、AWS Certificate Manager、Amazon Route 53 |
| セキュリティ・運用 | AWS WAF（レート制限）、CloudFront のセキュリティヘッダーポリシー、AWS Budgets（料金アラート）、Amazon CloudWatch Logs |
| IaC | AWS CloudFormation（配信基盤と CI/CD をテンプレート1つで構築） |
| CI/CD | AWS CodeBuild（GitHub の Webhook でテスト用・デプロイ用の2プロジェクトを実行） |
| 開発支援 | Claude Code（独自スキルによる仕様駆動開発・コードレビュー・セキュリティレビュー・ポートフォリオ取り込み） |

## アーキテクチャ

- **コンテンツ**: 自己紹介・ポートフォリオ・記事はすべて md ファイル。frontmatter がデータ（タイトル・タグなど）、本文が内容になり、ファイル名がそのまま URL のスラッグになる。
- **ビルド**: Astro のコンテンツコレクションで md を読み込み、ビルド時にすべてのページを静的 HTML にする。閲覧時のサーバー処理はない。
- **配信**: CloudFront から OAC で非公開の S3 バケットを読む。HTTPS へのリダイレクト・TLS 1.2 以上を強制し、CloudFront Functions で `/foo/` を `/foo/index.html` に補完する。403/404 は独自の 404 ページを返す。
- **CI/CD**: プルリクエストではテスト専用の CodeBuild（ログ権限のみ）が、指定ブランチへの push ではデプロイ用の CodeBuild が、テスト・lint・ビルドを通したうえで S3 に同期し、CloudFront のキャッシュを無効化する。
- **環境**: 本番と dev を同じテンプレートから別スタックとして作り、パラメーターだけで切り替える（`main` → 本番、`dev-release` → dev 環境）。

## 工夫した点

### コンテンツの追加が簡単で、壊れにくい

- 記事やポートフォリオは md ファイルを置くだけで追加できる。
- frontmatter の Zod スキーマを、ビルド時（コンテンツコレクション）と保存時（管理画面・コマンド）で共用し、判定がずれないようにした。
- md への書き込みは1つのモジュールに集約し、スラッグの検証・既存ファイルの上書き禁止・一時ファイル + rename による安全な置き換えを行う。
- ポートフォリオの URL はサイト内の相対パスも受け付け、本番・dev で同じ md を使える。見た目と違うパスになる制御文字・ゼロ幅文字・双方向制御文字は拒否する。

### 本番に出さない管理画面

- 管理画面と保存 API は、自作の Astro インテグレーションで `astro dev` のときだけ登録し、本番の成果物には一切含めない（ビルド成果物のテストと E2E で確認）。
- 保存 API は Origin・Content-Type の検査、本文サイズの上限（1 MB）、メソッドの制限を行う。ポートフォリオを追加する API はあえて用意せず、追加はコマンドに限定した。

### テストの厚さ

- 単体テストでは、スキーマ・md の解析・書き込み・並び順に加え、CloudFormation テンプレートと buildspec の設定値（非公開バケット、HTTPS 限定、IAM にワイルドカードの Action がないこと など）も検証する。
- E2E テストでは、全ページの共通構造、タイル全体のクリックやキーボード操作、幅 375・768・1280px のレスポンシブ表示、axe-core によるアクセシビリティ検査、管理画面の保存と API の防御を確認する。
- E2E の期待値は md から求めるため、コンテンツを書き換えてもテストを直す必要がない。

### セキュアでコストを抑えたインフラ

- デプロイ用のビルドでは `npm ci --ignore-scripts` で依存のインストールスクリプトを実行せず、乗っ取られた依存が権限のある環境で動かないようにした。
- テスト用とデプロイ用で CodeBuild と IAM ロールを分け、プルリクエストのビルドにはデプロイ権限を与えない。
- 静的配信 + CloudFront のキャッシュでランニングコストを小さく抑え、AWS Budgets で予算超過をメールで通知する。WAF はパラメーター1つで有効化できる。

### 他のポートフォリオをそのまま動かせる

- 取り込んだプロジェクトのフロントエンドを `apps/apps.json` に登録すると、デプロイ時にビルドして `/apps/<スラッグ>/` で配信する。
- バックエンドが必要なアプリは、ブラウザ上で `fetch` を横取りするモックを差し込み、サーバーなしで画面の動きを確認できる。

### AI と進める仕様駆動の開発

- 要件定義 → 設計 → タスク → 実装の順に進め、Claude Code の独自スキル（設計書の作成、設計から PR までの実装、コードレビュー、セキュリティレビュー、ポートフォリオの取り込み）で各工程を定型化した。
- 作業ごとに作業ログを残し、何を・なぜ変えたかを後から追えるようにしている。
