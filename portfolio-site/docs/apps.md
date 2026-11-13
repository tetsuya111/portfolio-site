# ポートフォリオのフロントエンドの配信（apps/）

ポートフォリオとして取り込んだプロジェクトのフロントエンドを、このサイトと同じ S3 バケット・CloudFront から `https://<ドメイン>/apps/<スラッグ>/` で配信する仕組み。取り込みはリポジトリの `/add-portfolio` スキル（[portfolio-importer](../../portfolios/portfolio-importer/README.md)）が行う。

## 構成

| 場所 | 内容 |
|---|---|
| `apps/<スラッグ>/` | フロントエンドのソース（取り込み時にコピーしたもの） |
| `apps/apps.json` | 配信するアプリの一覧（管理ファイル） |
| [`src/lib/apps-manifest.ts`](../src/lib/apps-manifest.ts) | `apps.json` の検証とビルド処理 |
| [`scripts/build-apps.mjs`](../scripts/build-apps.mjs) | `npm run build:apps` の入口 |

CloudFormation はリポジトリのファイルを直接読めないため、テンプレートで定義した CodeBuild の buildspec（`buildspec.yml`・`buildspec.test.yml`）が `astro build` の後に `npm run build:apps` を実行する。各アプリで `npm ci` と `npm run build -- <buildArgs>` を実行し（`package-lock.json` がないアプリはビルドせずエラーにする）、`<outputDir>` を `dist/apps/<スラッグ>/` にコピーする。デプロイは既存の `aws s3 sync dist` がそのまま行う。

## apps.json の書式

```json
{
  "apps": [
    { "slug": "my-app", "outputDir": "dist", "buildArgs": ["--base=/apps/my-app/"] }
  ]
}
```

| 項目 | 内容 |
|---|---|
| `slug` | スラッグ（ポートフォリオの md と同じ規則）。重複不可 |
| `outputDir` | ビルド成果物のディレクトリ（アプリ内の相対パス。`..`・絶対パス不可） |
| `buildArgs` | `npm run build --` に渡す引数。英数字と `@ . / : = - _` だけ |

不正な内容があると `npm run build:apps` が失敗し、ビルド（PR のテスト・デプロイとも）が止まる。

## 配信できるフロントエンド

S3 は静的配信のみのため、静的ファイルを出力できるものだけを登録する。

| 種類 | 出力先 | ベースパスの指定 |
|---|---|---|
| Vite | `dist` | `--base=/apps/<スラッグ>/` を自動で渡す |
| Astro | `dist` | `--base /apps/<スラッグ>/` を自動で渡す |
| Next.js（`output: "export"`・`basePath: "/apps/<スラッグ>"`・`trailingSlash: true` を設定済み） | `out` | `next.config` の `basePath`（3つのどれかが未設定なら登録されない） |

`package-lock.json` がないフロントエンドも登録されない。サーバー機能が必要なフロントエンド（`output: "export"` のない Next.js、`output: "server"` や adapter を使う Astro）と、Vite ベースのメタフレームワーク（SvelteKit・Nuxt・Remix など）は登録されない。

## 注意

- 存在しないパスへのアクセスはサイト共通の `/404.html` になる。クライアント側ルーティングの深いリンク（`/apps/x/foo` を直接開く）は動かない。
- `apps/<スラッグ>/` は取り込み時のコピーで、`portfolios/<スラッグ>/` 側の元のソースとは同期しない。配信内容を更新するときは `apps/<スラッグ>/` を編集する（または削除して取り込みを再実行する）。
- 登録したアプリのビルドが失敗すると、サイト全体のビルド・デプロイが止まる（不完全な状態で配信しないため）。急ぎでサイトだけ更新したいときは、`apps.json` から該当の項目を外す。
- アプリの依存はデプロイ用の CodeBuild（S3・CloudFront への書き込み権限あり）でインストール・ビルドされる。依存のインストールスクリプトやビルドプラグインもその権限で動くため、信頼できるプロジェクトだけを登録し、`package-lock.json` の変更はレビューする。
- 配信を止めるときは、`apps.json` から該当の項目を消し、`apps/<スラッグ>/` を削除する。
