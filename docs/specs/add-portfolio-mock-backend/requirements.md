# 要件定義: 取り込んだフロントエンドをバックエンドのモックと接続する

元の要望: [memo/claude/add-portfolio_バックエンドのモック化調査.md](../../../memo/claude/add-portfolio_バックエンドのモック化調査.md) と、`/superpowers-create-from-design-to-pr` の引数（「取り込んだフロントエンドのモックを作成し接続する」「docker-image を作成する処理を削除」）。

## 前提と仮定

無人実行のため、調査メモ・既存コードから次のとおり判断した。覆したい場合はこの節を起点に修正する。

| # | 仮定 | 根拠 |
|---|---|---|
| A1 | ベースは `main`。クローズされた PR #15（`--backend-url`・`apps.json` の `env`）の変更は含めない | PR #15 は未マージでクローズされ、「バックエンドを外部化すると料金がかかる」という今回の背景と逆の方向のため |
| A2 | モックはブラウザ内で `fetch` を横取りして応答する方式とし、**MSW は使わない**。依存のない小さなモックのランタイムを portfolio-site 側に置く | MSW を入れるにはアプリの `package.json`・`package-lock.json` を `npm install`（外部アクセス）で更新する必要がある。importer は Python 標準ライブラリだけで動き、lockfile を更新できない。調査メモの推奨理由（ブラウザ内で完結し、S3 だけで動く・POST も扱える）はこの方式でも満たせる |
| A3 | モックはアプリのソースを書き換えず、portfolio-site のビルド（`npm run build:apps`）で、出力 HTML の `<head>` にスクリプトを差し込んで接続する | Vite・Astro・Next.js の静的出力とも HTML を出力するため、フレームワークごとの組み込み処理が要らない。`apps/<スラッグ>/` のソースを自動で書き換えるのは壊れやすい |
| A4 | 横取りの対象は `fetch` だけ。`XMLHttpRequest`（axios の既定など）は対象外 | 調査対象のアプリ（spotify-billboard-playlist）は `fetch` を使う。XHR の模倣は実装量が大きい（YAGNI） |
| A5 | 「docker-image を作成する処理」には `--build-image`（`docker build`・`docker save`）に加え、イメージ作成のための Dockerfile・.dockerignore の生成も含めて削除する | S3 で完結させる前提では、バックエンドをコンテナで動かす予定がなく、Dockerfile は使われない |
| A6 | モックの雛形はバックエンドのルート定義（FastAPI・Flask のデコレーター、Express 系の `app.get(...)` など）から作り、応答の中身はスキル（Claude）がバックエンドのコードとフロントエンドの型から書く | 調査メモの「雛形だけ作って中身は手で書く形が現実的」。応答データを汎用的に推測するのは難しい |
| A7 | バックエンドが検出され、かつフロントエンドを配信登録した場合だけモックを作る | バックエンドのないフロントエンドにはモックが不要。配信しないフロントエンドにモックを付けても使われない |
| A8 | スラッグの予約名 `docker-images` は残す | 既存の `portfolios/docker-images/` が残っている環境でスラッグが衝突しないようにするため |

## 背景・課題

取り込んだフロントエンドは S3 に静的ファイルとして配信されるが、バックエンドがないため API を呼ぶ画面が動かない。バックエンドを EC2・VPS などで常駐させると料金がかかる。S3（と既存の CloudFront）だけで、ポートフォリオのデモとして画面を操作できるようにしたい。

## ゴール

- `/add-portfolio` で取り込んだフロントエンドが、S3 から配信された状態でバックエンドなしに API の応答（モック）を受け取って動く。
- 使われなくなった Docker イメージの作成処理がなくなる。

## Non-Goals（やらないこと）

- `XMLHttpRequest`・WebSocket・ページ遷移（`<a href="/auth/login">` など）の横取り
- 応答データの自動生成（雛形の生成まで。中身はスキルが書く）
- バックエンドを Lambda などで動かすこと
- 静的出力できないフロントエンド（spotify-billboard-playlist の Next.js 設定など）を静的出力できるようにする改修
- ローカルの `npm run dev` でのモックの接続（モックは `npm run build:apps` の成果物にだけ入る）

## 成功指標

- バックエンドのあるプロジェクトを取り込むと、`portfolio-site/apps/<スラッグ>/mock/handlers.js` に検出したルートの雛形ができ、`apps.json` に `"mock": true` が入る。
- `npm run build:apps` の成果物の各 HTML の `<head>` 先頭に、モックのスクリプトが入る。
- portfolio-importer と portfolio-site の `npm test`・`npm run lint` が成功する。

## ユーザーストーリー

- As a サイトの持ち主, I want 取り込んだフロントエンドがバックエンドなしで動いてほしい, so that サーバー代をかけずにポートフォリオのデモを見せられる。

## 機能要件（受け入れ基準）

### モックの雛形の作成（importer）

- **R1-1**: WHEN フロントエンドを配信登録し、かつバックエンドを検出した, THE SYSTEM SHALL `portfolio-site/apps/<スラッグ>/mock/handlers.js` にモックの雛形を作る。
- **R1-2**: THE SYSTEM SHALL 雛形に、バックエンドのソース（テストを除く）から検出したルート（メソッドとパス）ごとに1つのハンドラーを書く。
- **R1-3**: THE SYSTEM SHALL FastAPI・Flask のルートデコレーター（`@<名前>.get("/x")`・`@<名前>.route("/x", methods=[...])` など）と、node の `<名前>.get("/x", ...)` 形式（get・post・put・patch・delete）をルートとして検出する。
- **R1-4**: THE SYSTEM SHALL パスの引数（`{id}`・`<int:id>`）を `:id` の形に直して雛形に書く。
- **R1-5**: IF ルートを1つも検出できない, THEN THE SYSTEM SHALL ハンドラーの書き方の例だけを書いた雛形を作り、警告を出す。
- **R1-6**: IF `mock/handlers.js` が既にある, THEN THE SYSTEM SHALL 上書きせず、警告を出す。
- **R1-7**: WHEN モックの雛形を作った, THE SYSTEM SHALL 新しく追加する `apps.json` の項目に `"mock": true` を入れる。
- **R1-8**: IF `apps.json` に同じスラッグが登録済み, THEN THE SYSTEM SHALL 登録内容を変えず、`"mock": true` がなければ手で追加するよう警告を出す。
- **R1-9**: THE SYSTEM SHALL 結果の JSON の `frontend.mock` に雛形のパス（作らなかった場合は null）を、`backend.routes` に検出したルートの数を出す。
- **R1-10**: THE SYSTEM SHALL 雛形の各ハンドラーが既定で `portfolioMock.notFound()`（状態 404）を返すようにする。

### モックの接続（portfolio-site のビルド）

- **R2-1**: THE SYSTEM SHALL `apps.json` の項目の任意項目 `mock` として真偽値だけを受け付け、それ以外はエラーにする。
- **R2-2**: WHEN `mock` が true のアプリをビルドした, THE SYSTEM SHALL モックのランタイムと `mock/handlers.js` を `dist/apps/<スラッグ>/__mock__/` に置く。
- **R2-3**: WHEN `mock` が true のアプリをビルドした, THE SYSTEM SHALL `dist/apps/<スラッグ>/` 配下のすべての `.html` の `<head>` の直後に、ランタイム・ハンドラーの順で `<script>` を差し込む。
- **R2-4**: IF `mock` が true で `mock/handlers.js` がない, THEN THE SYSTEM SHALL そのアプリのビルドをエラーにする。

### モックのランタイム（ブラウザ）

- **R3-1**: THE SYSTEM SHALL `portfolioMock.handle(<メソッド>, <パス>, <応答を返す関数>)` でハンドラーを登録できるようにする。
- **R3-2**: WHEN 登録したメソッドとパスに一致する `fetch` が呼ばれた, THE SYSTEM SHALL 通信せず、ハンドラーの戻り値から作った応答を返す。
- **R3-3**: THE SYSTEM SHALL ハンドラーの戻り値が `Response` ならそのまま、`undefined`・null なら状態 204、それ以外の値なら状態 200 の JSON として応答する。
- **R3-4**: THE SYSTEM SHALL パスの `:名前` の部分を任意の1区間に一致させ、その値をハンドラーに渡す。
- **R3-5**: THE SYSTEM SHALL ハンドラーに、メソッド・パス・パスの引数・クエリ・リクエスト本文（JSON として読めれば変換した値）を渡す。
- **R3-6**: THE SYSTEM SHALL リクエスト先のパスがアプリの配信パス（`/apps/<スラッグ>`）で始まる場合、それを除いたパスでも一致を判定する。
- **R3-7**: WHEN 一致するハンドラーがない, THE SYSTEM SHALL 元の `fetch` で通信する。ただし宛先が `localhost`・`127.0.0.1`・`[::1]` なら、状態 404 の応答を返す（配信先に存在しないバックエンドへの通信エラーにしない）。
- **R3-8**: IF ハンドラーが例外を投げた, THEN THE SYSTEM SHALL 状態 500 ではなく状態 404 の応答を返す。
- **R3-9**: THE SYSTEM SHALL 状態 404 の JSON 応答を返す `portfolioMock.notFound()` を提供する。

### Docker イメージ作成処理の削除

- **R4-1**: THE SYSTEM SHALL `--build-image` オプションと、`docker build`・`docker save` によるイメージ作成をなくす。
- **R4-2**: THE SYSTEM SHALL バックエンドの Dockerfile・.dockerignore を生成しない。
- **R4-3**: THE SYSTEM SHALL 掲載 md のタグに `Docker` を自動で付けない。

### ドキュメント

- **R5-1**: THE SYSTEM SHALL スキル `/add-portfolio` の手順に、モックの雛形を仕上げる工程を含め、イメージ作成の工程をなくす。仕上げでは、正確な応答データより、フロントエンドが呼ぶ API がすべて 404 で答え 500・通信エラーにならないことを優先し、データは 404 で画面が表示できない箇所にだけ書く。
- **R5-2**: THE SYSTEM SHALL importer の README と配信の仕組みのドキュメント（`portfolio-site/docs/apps.md`）に、モックの作り方・制約を書く。

## 非機能要件

- **N1**: importer は Python 3.12 の標準ライブラリだけで動く（追加のインストールなし）。
- **N2**: モックのランタイムは依存パッケージを持たない1つの JavaScript ファイルとし、portfolio-site に依存を追加しない。
- **N3**: importer はリポジトリ外に書き込まず、既存のファイルを上書きしない。
