# 設計: 指定プロジェクトをポートフォリオとして追加するスキル

要件: [requirements.md](requirements.md)

## TL;DR

- スキル `.claude/skills/add-portfolio/` が、Python 製コマンド `python portfolios/portfolio-importer/add_portfolio.py <パス>` を呼ぶ。
- コマンドは「コピー → 検出 → フロントエンド登録 → Dockerfile 生成（とイメージ作成） → 掲載 md 作成」を順に行い、結果を JSON で返す。
- フロントエンドは `portfolio-site/apps/<スラッグ>/` に置き、`portfolio-site/apps/apps.json` に登録する。デプロイ用 buildspec が `npm run build:apps` で各アプリをビルドして `dist/apps/<スラッグ>/` に置き、既存の `s3 sync dist` で配信される。

## Non-Goals

requirements.md のとおり。レジストリへの push・VPS 起動・静的出力できないフロントエンドの改修は行わない。

## 全体構成

```
/add-portfolio <パス>（スキル）
  └ python portfolios/portfolio-importer/add_portfolio.py <パス> [--slug] [--site-url] [--build-image]
       importer/cli.py        引数解析・全体の順序・JSON 出力
       importer/ignore.py     .gitignore 互換の除外判定（R1-3, R1-4）
       importer/copier.py     コピー先の決定とコピー（R1-*）
       importer/detect.py     フロントエンド・バックエンドの検出（R2-1, R2-2, R3-1）
       importer/frontend.py   apps/ へのコピーと apps.json 登録（R2-1, R2-2）
       importer/backend.py    Dockerfile・.dockerignore 生成、docker build/save（R3-*）
       importer/content.py    掲載 md の作成（R4-*）
portfolio-site/
  apps/apps.json              配信の管理ファイル（R2-1）
  scripts/apps-manifest.mjs   apps.json の検証（R2-4）
  scripts/build-apps.mjs      各アプリのビルドと dist/apps への配置（R2-3）
  buildspec.yml               test:build の後に build:apps を実行（R2-3）
  infra/template.yaml         出力 AppsBaseUrl を追加
```

## 各部の設計

### コピー（copier.py, ignore.py）

- リポジトリルートは `add_portfolio.py` の位置から決める（`portfolios/portfolio-importer/` の2つ上）。関数はすべて `repo_root` を引数で受け取り、テストでは一時ディレクトリを使う。
- `resolve_target(source, repo_root, slug)`:
  - `source` を `resolve()` し、ディレクトリでなければエラー。
  - `portfolios/` 配下なら `portfolios/<最初の階層>` を対象にし、コピーしない（R1-2）。スラッグはそのディレクトリ名。
  - リポジトリルートを含む、またはリポジトリ内の `portfolios/` 外ならエラー（R1-6）。
  - それ以外は `portfolios/<スラッグ>` が既にあればエラー（R1-5）。
- スラッグ: ディレクトリ名を小文字化し、英数字以外の連続を `-` に置換して前後の `-` を除く。検証は R1-7 の正規表現と予約名。
- `IgnoreMatcher`: 各階層の `.gitignore` を読み込み、git と同じく「最後に一致した規則が勝つ」「除外されたディレクトリの中は見ない」で判定する。対応する書式は `#` コメント・`!` 否定・末尾 `/`（ディレクトリのみ）・先頭または途中の `/`（そのディレクトリからの相対）・`*`・`?`・`**`・`[...]`。
- 常に除外（`.gitignore` の否定でも戻さない）: `.git/`、`*.sqlite`・`*.sqlite3`・`*.db` と `-journal`・`-wal`・`-shm` 付きのもの、`.env`・`.env.*`（`.env.example` は除外しない）、シンボリックリンク。
- 同じ判定器をフロントエンドの `apps/` へのコピーにも使う。

### 検出（detect.py）

- フロントエンド: `frontend/`・`web/`・`client/`・ルートの順に、`package.json` に `scripts.build` があるディレクトリを探す。依存（dependencies + devDependencies）で種類を決める。

  | 判定 | 種類 | 出力先 | ビルド引数 |
  |---|---|---|---|
  | `next` あり、`next.config.*` に `output: "export"` と `basePath: "/apps/<スラッグ>"` | next-export | `out` | なし |
  | `next` あり、basePath なし | 配信不可（警告） | — | — |
  | `astro` で `output: "server"/"hybrid"` か adapter あり | 配信不可（警告） | — | — |
  | SvelteKit・Nuxt・Remix などの Vite メタフレームワーク | 配信不可（警告） | — | — |
  | `next` あり、上記以外 | 配信不可（警告） | — | — |
  | `astro` | astro | `dist` | `--base /apps/<スラッグ>/` |
  | `vite` | vite | `dist` | `--base=/apps/<スラッグ>/` |
  | それ以外 | 配信不可（警告） | — | — |

- バックエンド: `backend/`・`server/`・`api/` に `pyproject.toml`・`requirements.txt`（python）か、`package.json`（node）があるもの。なければルートに `pyproject.toml`・`requirements.txt` があればルートを python バックエンドとする。ルートの `package.json` が `express`・`fastify`・`koa`・`@nestjs/core`・`hono` に依存し、フロントエンドとして検出されていなければ node バックエンドとする。
- 検出した技術はタグ候補として返す（Python・FastAPI・Node.js・React・Next.js・Vite・Astro・Docker など）。

### バックエンド（backend.py）

- Python の Dockerfile: `python:3.12-slim`、`pip install --no-cache-dir .`（pyproject）または `-r requirements.txt`、非 root ユーザー、`EXPOSE 8000`。
  - 起動コマンド: バックエンド内の `.py`・README に `uvicorn <モジュール>:<属性> [--factory]` の記載があればそれを、なければ `<名前> = FastAPI(` の代入があるファイルから組み立てる。いずれも `--host 0.0.0.0 --port 8000` を付ける。`main.py` しかなければ `python main.py`。
- node の Dockerfile: `node:22-slim`、`npm ci --omit=dev`（lock がなければ `npm install --omit=dev`）、`USER node`、`EXPOSE 3000`、`scripts.start` があれば `npm start`。
- 起動コマンドが決まらなければ `CMD` を書かずに編集を促すコメントを入れ、イメージを作らない（R3-2）。
- 既存の `Dockerfile`・`.dockerignore` は上書きしない（警告）。
- イメージ: `--build-image` のときだけ `docker build -t portfolio-<スラッグ>-backend:latest <dir>`、`docker save -o portfolios/docker-images/<スラッグ>-backend.tar <タグ>`。`portfolios/docker-images/.gitignore`（`*.tar`）を無ければ作る。`subprocess.run` は引数リストで呼び、テストでは差し替える。

### フロントエンド（frontend.py と portfolio-site 側）

- `portfolio-site/apps/<スラッグ>/` がなければ除外規則つきでコピーする。あればコピーしない（警告）。
- `apps.json` の形式: `{"apps": [{"slug": "...", "outputDir": "dist", "buildArgs": ["--base=/apps/x/"]}]}`。同じスラッグがあれば更新しない。キー順・2スペースインデントで書き出す。
- `scripts/apps-manifest.mjs` の `validateManifest(data)`: スラッグ形式・重複、`outputDir` が相対パスで `..` を含まない、`buildArgs` の各要素が `^[\w@./:=-]+$`。不正なら例外（R2-4）。
- `scripts/build-apps.mjs`: 検証後、各アプリで `npm ci`（lock がなければ `npm install`）と `npm run build -- <buildArgs>` を実行し、`<outputDir>` を `dist/apps/<スラッグ>/` にコピーする。どれかが失敗したら終了コード 1。`spawnSync` は Windows のみ `shell: true`（引数は上記の正規表現で検証済み）。
- `/apps/<スラッグ>/` の `index.html` 解決は既存の `DirectoryIndexFunction` がそのまま担う。
- `apps/` は portfolio-site の ESLint・`astro check`（tsconfig）の対象から外す。

### 掲載（content.py）

- 入力の優先順: `portfolios/docs/<スラッグ>.md`（frontmatter と本文）→ プロジェクトの `README.md`（最初の `# 見出し` をタイトル、残りを本文）→ スラッグ。
- frontmatter の読み取りは `key: value` と `- 項目` のリストだけを扱う簡易パーサー。書き出しは値を JSON 文字列（YAML のダブルクォート文字列として有効）で書く。
- 本文の先頭にある `# 見出し` 1行は除く（サイトがタイトルを h1 で出すため）。
- `tags`: docs のタグがあればそれ、なければ検出した技術。`date`: 実行日。`url`: R4-3 の条件のときだけ。http/https でない値は捨てる。
- 既にファイルがあれば作らない（R4-4）。

### コマンド出力（cli.py）

```json
{"slug": "...", "projectDir": "portfolios/...", "copied": true,
 "frontend": {"dir": "...", "kind": "vite", "registered": true} ,
 "backend": {"dir": "...", "kind": "python", "dockerfile": "...", "image": null},
 "content": "portfolio-site/src/content/portfolios/....md", "warnings": ["..."]}
```

### スキル（SKILL.md）

1. 引数のパスを確認。リポジトリ外へ書き込む操作はコマンドにないため確認不要（読むだけ）。
2. まず `--build-image` なしでコマンドを実行し JSON を読む。
3. バックエンドがあり Dockerfile に CMD がある場合、`docker build` がベースイメージを外部から取得することを伝えて yes/no を確認し、yes なら対象を `portfolios/<スラッグ>`（コピー済みの場所）にして `--build-image` 付きで再実行する（`portfolios/` 配下はコピーせず、既存の生成物も上書きしないので再実行しても安全）。
4. 作成された掲載 md を読み、本文の相対リンク・見出しレベルを直す。
5. `portfolio-site` で `npm test`・`npm run lint` を実行して確認し、`logs/` に作業ログを書き、結果（警告を含む）を報告する。

## 横断的関心事

- **セキュリティ**: `.env`・DB は常に除外する。シンボリックリンクはたどらない（リポジトリ外のファイルを取り込まない）。`docker` は `shell=False` で実行。`apps.json` の引数は正規表現で制限する。
- **冪等性**: 既存ファイルは上書きしないので、同じプロジェクトで再実行しても既存の成果物を壊さない（コピーだけはコピー先が存在するとエラー）。
- **既存構成との整合**: デプロイは既存 buildspec の `s3 sync dist --delete` をそのまま使う。テスト用 buildspec（PR）では `build:apps` を実行しない。

## 検討した代替案

- CloudFormation でアプリごとに S3 バケット・ディストリビューションを作る: ドメイン・証明書の追加が必要になり、1スタック構成から大きく外れるため不採用。
- 外部 YAML ライブラリ（PyYAML）・pytest を使う: パッケージ取得が確認対象になり、無人で動かせないため標準ライブラリ（unittest）にした。
- `git ls-files` で除外を判定する: 指定プロジェクトが git リポジトリとは限らないため、独自の `.gitignore` 判定器にした。
- Docker イメージの tar を git 管理する: サイズが大きすぎるため管理対象外にした。

## 残っている判断（実装者に任せる）

- `.gitignore` の書式のうち、エスケープ（`\#`・`\!`）や末尾空白の扱いは簡易対応でよい。
