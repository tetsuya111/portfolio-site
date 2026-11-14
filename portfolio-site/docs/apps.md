# ポートフォリオのフロントエンドの配信（apps/）

ポートフォリオとして取り込んだプロジェクトのフロントエンドを、このサイトと同じ S3 バケット・CloudFront から `https://<ドメイン>/apps/<スラッグ>/` で配信する仕組み。取り込みはリポジトリの `/add-portfolio` スキル（[portfolio-importer](../../portfolios/portfolio-importer/README.md)）が行い、`--register-frontend` を明示したときだけ登録する。

## 構成

| 場所 | 内容 |
|---|---|
| `apps/<スラッグ>/` | フロントエンドのソース（取り込み時にコピーしたもの） |
| `apps/apps.json` | 配信するアプリの一覧（管理ファイル） |
| [`src/lib/apps-manifest.ts`](../src/lib/apps-manifest.ts) | `apps.json` の検証とビルド処理 |
| [`scripts/build-apps.mjs`](../scripts/build-apps.mjs) | `npm run build:apps` の入口 |
| `apps/<スラッグ>/mock/handlers.js` | バックエンドのモックのハンドラー（`mock: true` のアプリ） |
| [`src/lib/mock-runtime.js`](../src/lib/mock-runtime.js) | ブラウザで `fetch` を横取りするモックのランタイム |

CloudFormation はリポジトリのファイルを直接読めないため、テンプレートで定義した CodeBuild の buildspec（`buildspec.yml`・`buildspec.test.yml`）が `astro build` の後に `npm run build:apps` を実行する。各アプリで `npm ci` と `npm run build -- <buildArgs>` を実行し（`package-lock.json` がないアプリはビルドせずエラーにする）、`<outputDir>` を `dist/apps/<スラッグ>/` にコピーする（`mock: true` ならモックを差し込む）。デプロイは既存の `aws s3 sync dist` がそのまま行う。

## apps.json の書式

```json
{
  "apps": [
    { "slug": "my-app", "outputDir": "dist", "buildArgs": ["--base=/apps/my-app/"], "mock": true }
  ]
}
```

| 項目 | 内容 |
|---|---|
| `slug` | スラッグ（ポートフォリオの md と同じ規則）。重複不可 |
| `outputDir` | ビルド成果物のディレクトリ（アプリ内の相対パス。`..`・絶対パス不可） |
| `buildArgs` | `npm run build --` に渡す引数。英数字と `@ . / : = - _` だけ |
| `mock`（任意） | `true` ならバックエンドのモックを差し込む（[バックエンドのモック](#バックエンドのモック)）。省略時は `false` |

不正な内容があると `npm run build:apps` が失敗し、ビルド（PR のテスト・デプロイとも）が止まる。

## 配信できるフロントエンド

S3 は静的配信のみのため、静的ファイルを出力できるものだけを登録する。

| 種類 | 出力先 | ベースパスの指定 |
|---|---|---|
| Vite | `dist` | `--base=/apps/<スラッグ>/` を自動で渡す |
| Astro | `dist` | `--base /apps/<スラッグ>/` を自動で渡す |
| Next.js（`output: "export"`・`basePath: "/apps/<スラッグ>"`・`trailingSlash: true` を設定済み） | `out` | `next.config` の `basePath`（3つのどれかが未設定なら登録されない） |

`package-lock.json` がないフロントエンドも登録されない。サーバー機能が必要なフロントエンド（`output: "export"` のない Next.js、`output: "server"` や adapter を使う Astro）と、Vite ベースのメタフレームワーク（SvelteKit・Nuxt・Remix など）は登録されない。

## バックエンドのモック

S3 ではバックエンドを動かせないため、バックエンドのあるプロジェクトは、ブラウザ内で API に応答するモックで動かす（サーバーを常駐させず、料金をかけないため）。取り込み時に importer がバックエンドのルートから `apps/<スラッグ>/mock/handlers.js` の雛形を作り、`/add-portfolio` スキルが応答データを書く。

`mock: true` のアプリは、`npm run build:apps` が次を行う（`mock/handlers.js` がなければビルドをエラーにする）。

1. ランタイムと `handlers.js` を `dist/apps/<スラッグ>/__mock__/runtime.js`・`handlers.js` に置く。
2. 出力のすべての `.html` の `<head>` 直後に、2つを読み込む `<script>` を差し込む。アプリのスクリプトより先に実行され、`window.fetch` を差し替える。

`handlers.js` の書き方:

```js
portfolioMock.handle("GET", "/api/me", () => ({ name: "Demo User" }));
portfolioMock.handle("POST", "/api/items/:id", (req) => ({ id: req.params.id, ...req.body }));
```

- `req` は `{ method, path, params, query（URLSearchParams）, body（JSON なら変換済み） }`。
- 戻り値: オブジェクトなど → 200 の JSON／`undefined`・`null` → 204／`new Response(...)` → そのまま。`async` も可。例外は 500 になる。
- パスは、リクエスト先のパスと、`/apps/<スラッグ>` を除いたパスの両方で一致を調べる。横取りするのは、アプリと同じオリジンと `localhost`・`127.0.0.1`（開発時のバックエンドの URL のまま呼ぶフロントエンド向け）だけで、外部の API はそのまま通信する。パスの `:名前` は、ファイル名に見える区間（`1.txt` など）には一致しない（静的ファイル・ページデータの取得を横取りしないため）。一致しないリクエストは通常どおり通信する。

制約:

- 横取りするのは `fetch` だけ。`XMLHttpRequest`（axios の既定など）・WebSocket・ページ遷移（`<a href="/auth/login">` など）は横取りしない。
- `npm run build:apps` の成果物にだけ入る。アプリの `npm run dev` では動かない。
- `handlers.js` は公開されるため、秘密情報を書かない。

## 注意

- 存在しないパスへのアクセスはサイト共通の `/404.html` になる。クライアント側ルーティングの深いリンク（`/apps/x/foo` を直接開く）は動かない。
- `apps/<スラッグ>/` は取り込み時のコピーで、`portfolios/<スラッグ>/` 側の元のソースとは同期しない。配信内容を更新するときは `apps/<スラッグ>/` を編集する（または削除して取り込みを再実行する）。
- 登録したアプリのビルドが失敗すると、サイト全体のビルド・デプロイが止まる（不完全な状態で配信しないため）。急ぎでサイトだけ更新したいときは、`apps.json` から該当の項目を外す。
- アプリの依存はデプロイ用の CodeBuild（S3・CloudFront への書き込み権限あり）でインストール・ビルドされる。依存のインストールスクリプトやビルドプラグインもその権限で動くため、信頼できるプロジェクトだけを登録し、`package-lock.json` の変更はレビューする。
- 配信を止めるときは、`apps.json` から該当の項目を消し、`apps/<スラッグ>/` を削除する。
