# ポートフォリオのフロントエンドの配信（apps/）

ポートフォリオとして取り込んだプロジェクトのフロントエンドを、このサイトと同じ S3 バケット・CloudFront から `https://<ドメイン>/apps/<スラッグ>/` で配信する仕組み。取り込みはリポジトリの `/add-portfolio` スキル（[portfolio-importer](../../portfolios/portfolio-importer/README.md)）が行う。

## 構成

| 場所 | 内容 |
|---|---|
| `apps/<スラッグ>/` | フロントエンドのソース（取り込み時にコピーしたもの） |
| `apps/apps.json` | 配信するアプリの一覧（管理ファイル） |
| [`src/lib/apps-manifest.ts`](../src/lib/apps-manifest.ts) | `apps.json` の検証とビルド処理 |
| [`scripts/build-apps.mjs`](../scripts/build-apps.mjs) | `npm run build:apps` の入口 |

CloudFormation はリポジトリのファイルを直接読めないため、テンプレートで定義した CodeBuild の buildspec（`buildspec.yml`・`buildspec.test.yml`）が `astro build` の後に `npm run build:apps` を実行する。各アプリで `npm ci`（lock がなければ `npm install`）と `npm run build -- <buildArgs>` を実行し、`<outputDir>` を `dist/apps/<スラッグ>/` にコピーする。デプロイは既存の `aws s3 sync dist` がそのまま行う。

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
| Next.js（`output: "export"` 設定済み） | `out` | `next.config` の `basePath` に `/apps/<スラッグ>` を自分で設定する |

サーバー機能が必要なフロントエンド（`output: "export"` のない Next.js など）は登録されない。

## 注意

- 存在しないパスへのアクセスはサイト共通の `/404.html` になる。クライアント側ルーティングの深いリンク（`/apps/x/foo` を直接開く）は動かない。
- 配信を止めるときは、`apps.json` から該当の項目を消し、`apps/<スラッグ>/` を削除する。
