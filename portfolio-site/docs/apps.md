# ポートフォリオのフロントエンドの配信（apps/）

ポートフォリオとして取り込んだプロジェクトのフロントエンドを、このサイトと同じ S3 バケット・CloudFront から `https://<ドメイン>/apps/<スラッグ>/` で配信する仕組み。取り込みはリポジトリの `/add-portfolio` スキル（[portfolio-importer](../../portfolios/portfolio-importer/README.md)）が行い、`--register-frontend` を明示したときだけ登録する。

## 構成

| 場所 | 内容 |
|---|---|
| `apps/<スラッグ>/` | フロントエンドのソース（取り込み時にコピーしたもの） |
| `apps/apps.json` | 配信するアプリの一覧（管理ファイル） |
| [`src/lib/apps-manifest.ts`](../src/lib/apps-manifest.ts) | `apps.json` の検証とビルド処理 |
| [`scripts/build-apps.mjs`](../scripts/build-apps.mjs) | `npm run build:apps` の入口 |

CloudFormation はリポジトリのファイルを直接読めないため、テンプレートで定義した CodeBuild の buildspec（`buildspec.yml`・`buildspec.test.yml`）が `astro build` の後に `npm run build:apps` を実行する。各アプリで `npm ci` と `npm run build -- <buildArgs>`（`env` はこのビルドにだけ環境変数として追加する）を実行し（`package-lock.json` がないアプリはビルドせずエラーにする）、`<outputDir>` を `dist/apps/<スラッグ>/` にコピーする。デプロイは既存の `aws s3 sync dist` がそのまま行う。

## apps.json の書式

```json
{
  "apps": [
    {
      "slug": "my-app",
      "outputDir": "dist",
      "buildArgs": ["--base=/apps/my-app/"],
      "env": { "VITE_API_URL": "https://api.example.com" }
    }
  ]
}
```

| 項目 | 内容 |
|---|---|
| `slug` | スラッグ（ポートフォリオの md と同じ規則）。重複不可 |
| `outputDir` | ビルド成果物のディレクトリ（アプリ内の相対パス。`..`・絶対パス不可） |
| `buildArgs` | `npm run build --` に渡す引数。英数字と `@ . / : = - _` だけ |
| `env`（任意） | ビルド時の環境変数。バックエンドの URL などを渡す。名前は `VITE_`・`PUBLIC_`・`NEXT_PUBLIC_` で始まる英大文字・数字・`_` だけ、値は `https://` の URL（英数字と `. - _ ~ /` だけ、クエリなし）だけ |

不正な内容があると `npm run build:apps` が失敗し、ビルド（PR のテスト・デプロイとも）が止まる。

`env` は取り込み時に `--backend-url` を付けると書かれる（環境変数名はフロントエンドのソースから推測する）。付けなかった場合や名前が違う場合は手で書く。`.env.*` は取り込み時にコピーされず、git の管理外のため、ビルドに値を渡すにはこの `env` を使う。値はフロントエンドのファイルに埋め込まれ公開されるため、秘密情報は書かない。バックエンドはサイトのオリジン（`https://<ドメイン>`）からの CORS を許可しておく。

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
