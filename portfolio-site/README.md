# ポートフォリオサイト

フリーランスエンジニアのポートフォリオサイトです。自己紹介・経歴、ポートフォリオ、記事をすべて md ファイルで管理し、Astro で静的サイトとしてビルドして、AWS（S3 + CloudFront）で配信します。

- フロントエンド: [Astro](https://astro.build/)（静的出力）+ [Tailwind CSS](https://tailwindcss.com/) v4
- 配信: S3（非公開）+ CloudFront（OAC）+ ACM + Route 53
- CI/CD: CodeBuild（GitHub と連携。`main` 向けの PR でテスト、`main` への push でデプロイ）

## 必要なもの

- Node.js 22.23.4 以上（Astro 7 の要件）
- AWS へデプロイする場合: [docs/infra-setup.md](docs/infra-setup.md) を参照

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
| `npm run test:e2e` | Playwright の E2E テスト（公開ページと管理画面をブラウザで操作して検証）。初回のみ `npx playwright install chromium` が必要 |
| `npm run lint` | ESLint と型チェック（`astro check`） |
| `npm run portfolio:new` | ポートフォリオを追加する（下記） |

## コンテンツの更新

自己紹介・ポートフォリオ・記事は `src/content/` 配下の md ファイルです。どの方法でも md ファイルが更新されるだけなので、公開するには変更をコミットして `main` に push します。

| 種類 | 追加・更新の方法 |
|---|---|
| 自己紹介・経歴 | `src/content/profile/profile.md` を編集、または `npm run dev` 中に管理画面 `/admin/profile/` |
| ポートフォリオ | `npm run portfolio:new -- --slug my-app --title "My App" --tags "Astro,AWS"`、または md を直接置く（サイト上からは追加できない） |
| 記事 | `src/content/articles/` に md を置く、または `npm run dev` 中に管理画面 `/admin/articles/new/` |

各ファイルの項目・書式・スラッグのルール・管理画面の制限は [docs/content-files.md](docs/content-files.md) にまとめています。

## AWS への構築・デプロイ

S3 + CloudFront での配信と、CodeBuild による CI/CD の構成・削除方法は [infra/README.md](infra/README.md)、構築手順は [docs/infra-setup.md](docs/infra-setup.md) にまとめています。

概要だけ示すと、us-east-1 に CloudFormation スタックを1つ作成したあと、`portfolio-site/` 配下の変更を次のように扱います。

- `main`（本番スタックの `DeployBranch`）向けのプルリクエスト: CodeBuild がテスト・lint・ビルドを実行し、結果を GitHub に表示（ほかのブランチ向けの PR ではテストしない）
- `main` への push: 同じ処理が成功したら、S3 に反映して CloudFront のキャッシュを無効化
