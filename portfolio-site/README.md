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
| サービス・スキル・こんな方とお話ししたい（トップページ） | `src/content/services/`・`src/content/skills/`・`src/content/audiences/` の md を編集・追加 |

各ファイルの項目・書式・スラッグのルール・管理画面の制限は [docs/content-files.md](docs/content-files.md) にまとめています。

## トップページの相談ボタン

トップページ冒頭の「ご相談はこちら」の2つのボタンは、ビルド時の環境変数で動きが決まります。

| 環境変数 | 内容 | 未設定・不正なとき |
|---|---|---|
| `PUBLIC_CONTACT_EMAIL` | 「フォームで相談する」の宛先メールアドレス。フォームの送信で、入力内容を書き込んだ mailto: リンクを開く（サイトには何も送らない） | フォームのボタンを出さない |
| `PUBLIC_TASK_BOX_URL` | 「タスク百葉箱で相談する」の遷移先（http(s) の URL か `/` で始まるサイト内のパス。外部 URL は別タブで開く） | `src/site.config.ts` の `taskBoxMockUrl`（既定はデモの `/apps/task-box-it-develop/`）。それも空ならボタンを「準備中」にして遷移しない |

```bash
PUBLIC_CONTACT_EMAIL=you@example.com PUBLIC_TASK_BOX_URL=https://task-box.example.com/ npm run build
```

- メールアドレスは公開ページの HTML にそのまま入ります。公開してよい問い合わせ用のアドレスを使ってください。
- AWS の CodeBuild（`infra/template.yaml`）にはこれらを渡す設定がまだありません。本番で使うには、デプロイ用の CodeBuild プロジェクトの環境変数に設定してください（コンソールで足した値はスタックの更新で消えるため、テンプレートへの追加は別途対応）。

## デザインテーマの切り替え

公開ページのデザインは `minimal`（既定）と `campus` から選べます。公開するサイトのテーマは `src/site.config.ts` の `theme` で指定します。手元で別のテーマを試すときは、ビルド時に環境変数で上書きできます。

```bash
PUBLIC_THEME=campus npm run build
```

テーマの中身・追加方法は [docs/themes.md](docs/themes.md) を参照してください。

## AWS への構築・デプロイ

S3 + CloudFront での配信と、CodeBuild による CI/CD の構成・削除方法は [infra/README.md](infra/README.md)、構築手順は [docs/infra-setup.md](docs/infra-setup.md) にまとめています。

概要だけ示すと、us-east-1 に CloudFormation スタックを1つ作成したあと、`portfolio-site/` 配下の変更を次のように扱います。

- `main`（本番スタックの `DeployBranch`）向けのプルリクエスト: CodeBuild がテスト・lint・ビルドを実行し、結果を GitHub に表示（ほかのブランチ向けの PR ではテストしない）
- `main` への push: 同じ処理が成功したら、S3 に反映して CloudFront のキャッシュを無効化
