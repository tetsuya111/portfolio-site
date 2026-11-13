# ポートフォリオサイト

フリーランスエンジニアのポートフォリオサイトです。自己紹介・経歴、ポートフォリオ、記事をすべて md ファイルで管理し、Astro で静的サイトとしてビルドして、AWS（S3 + CloudFront）で配信します。

- フロントエンド: [Astro](https://astro.build/)（静的出力）+ [Tailwind CSS](https://tailwindcss.com/) v4
- 配信: S3（非公開）+ CloudFront（OAC）+ ACM + Route 53
- CI/CD: CodeBuild（GitHub と連携。PR でテスト、`main` への push でデプロイ）

## 必要なもの

- Node.js 22.23.4 以上（Astro 7 の要件）
- AWS へデプロイする場合: [infra/README.md](infra/README.md) の「前提」を参照

## ディレクトリ構成

コンテンツは `src/content/` 配下の md ファイル（`profile/profile.md`・`portfolios/*.md`・`articles/*.md`）です。ディレクトリ構成と各ファイルの役割・つながりは [docs/project-structure.md](docs/project-structure.md) にまとめています。

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

## AWS への構築・デプロイ

S3 + CloudFront での配信と、CodeBuild による CI/CD の構成・構築手順・削除方法は [infra/README.md](infra/README.md) にまとめています。

概要だけ示すと、us-east-1 に CloudFormation スタックを1つ作成したあと、`portfolio-site/` 配下の変更を次のように扱います。

- プルリクエスト: CodeBuild がテスト・lint・ビルドを実行し、結果を GitHub に表示
- `main` への push: 同じ処理が成功したら、S3 に反映して CloudFront のキャッシュを無効化
