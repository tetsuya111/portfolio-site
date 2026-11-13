# ポートフォリオ追加スキル 実装計画

> **For agentic workers:** superpowers:test-driven-development で1タスクずつ進める。チェックボックス（`- [ ]`）で進捗を管理する。

**Goal:** パス1つの指定で、プロジェクトを `portfolios/` に取り込み、配信・コンテナ化の準備とサイト掲載まで行うスキルとコマンドを作る。

**Architecture:** Python 標準ライブラリ製のコマンド `portfolios/portfolio-importer/` を、スキル `.claude/skills/add-portfolio/` から呼ぶ。フロントエンドの配信は `portfolio-site/apps/apps.json` を buildspec 経由のビルドスクリプトが読む。

**Tech Stack:** Python 3.12（unittest）、Node.js 22（vitest）、Docker CLI、CloudFormation

**Spec:** [requirements.md](requirements.md)・[design.md](design.md)

## Global Constraints

- Python は標準ライブラリのみ。外部パッケージを取得しない。
- コマンドはリポジトリ外に書き込まない。既存の生成物は上書きしない。
- スラッグ: `^[a-z0-9]+(?:-[a-z0-9]+)*$`、予約名 `docs`・`docker-images`・`portfolio-importer`。
- テスト実行: `portfolios/portfolio-importer` で `npm test`（= `python -m unittest discover -s tests -t .`）、`npm run lint`（= `python -m compileall -q importer tests add_portfolio.py`）。portfolio-site は `npm test`・`npm run lint`。

## Review Focus

- `.gitignore` の否定規則で、除外されたディレクトリ配下のファイルを戻そうとした場合 → 戻さない（git と同じ）。Task 1 でテスト。
- Windows のパス区切り（`\`）で `.gitignore` 判定が崩れる → 判定は常に `/` 区切りの相対パスで行う。Task 1 でテスト。
- `portfolios/` 配下のサブディレクトリ（例 `portfolios/x/backend`）を指定 → `portfolios/x` を対象にする。Task 2 でテスト。
- docs の frontmatter に `url: ""` がある（既存の spotify の docs） → url を入れない。Task 6 でテスト。
- `apps.json` に `../` を含む outputDir → 検証で失敗。Task 7 でテスト。

---

### Task 1: 除外判定（R1-3, R1-4）

**Files:** Create `portfolios/portfolio-importer/{package.json,add_portfolio.py,importer/__init__.py,importer/ignore.py}`, Test `tests/test_ignore.py`

**Interfaces:** Produces `IgnoreMatcher(root: Path)`、`.is_excluded(rel_path: str, is_dir: bool) -> bool`、`.add_gitignore(dir_rel: str) -> None`（walk 中に各階層の .gitignore を読み込む）、`iter_files(root: Path) -> Iterator[Path]`（除外を適用した相対ファイルパス）。

- [ ] テスト: `*.log` がどの階層でも除外 / `/build` はルート直下のみ / `data/` はディレクトリのみ / `!keep.log` で戻る / 除外ディレクトリ配下の `!` は戻らない / `a/**/b` / サブディレクトリの .gitignore はその配下だけに効く / `.git`・`x.sqlite`・`x.db-wal`・`.env`・`.env.local` は常に除外・`.env.example` は残る / シンボリックリンクは iter_files に出ない（作成できない環境では skip）
- [ ] 失敗確認 → 実装 → `npm test` 成功 → コミット

### Task 2: コピー先の決定とコピー（R1-1, R1-2, R1-5, R1-6, R1-7）

**Files:** Create `importer/copier.py`, Test `tests/test_copier.py`

**Interfaces:** Produces `make_slug(name: str) -> str`、`validate_slug(slug: str) -> None`（不正時は `importer/__init__.py` に定義する `PortfolioError(Exception)` を送出。以降のエラーもすべてこれ）、`resolve_target(source: Path, repo_root: Path, slug: str | None) -> Target`（`Target(slug, project_dir: Path, copy_from: Path | None)`）、`copy_tree(src: Path, dest: Path) -> int`（コピーしたファイル数）。

- [ ] テスト: `My_App 2` → `my-app-2` / 予約名・不正スラッグでエラー / portfolios 外 → copy_from あり / `portfolios/x/backend` → project_dir=`portfolios/x`・copy_from=None / コピー先既存でエラー / リポジトリルートやリポジトリ内 portfolios 外でエラー / ファイル指定でエラー / copy_tree が除外を適用する
- [ ] 失敗確認 → 実装 → 成功 → コミット

### Task 3: 検出（R2-1, R2-2, R3-1）

**Files:** Create `importer/detect.py`, Test `tests/test_detect.py`

**Interfaces:** Produces `detect_frontend(project: Path, slug: str) -> Frontend | None`（`Frontend(dir: Path, kind: str | None, output_dir: str | None, build_args: list[str], reason: str | None, tags: list[str])`、配信不可は kind=None と reason）、`detect_backend(project: Path, frontend: Frontend | None) -> Backend | None`（`Backend(dir: Path, kind: "python"|"node", tags: list[str])`）。

- [ ] テスト: vite → `dist`・`--base=/apps/<slug>/` / astro → `--base`,`/apps/<slug>/` / next + `output: "export"` → `out` / next のみ → 配信不可 / build スクリプトなし → None / `backend/pyproject.toml` → python / ルート requirements.txt → python / ルート express 依存 → node / FastAPI 依存でタグ `FastAPI`
- [ ] 失敗確認 → 実装 → 成功 → コミット

### Task 4: Dockerfile とイメージ（R3-1〜R3-3）

**Files:** Create `importer/backend.py`, Test `tests/test_backend.py`

**Interfaces:** Consumes `Backend`。Produces `write_docker_files(backend: Backend) -> DockerResult`（`DockerResult(dockerfile: Path, has_cmd: bool, warnings: list[str])`）、`build_image(backend_dir: Path, slug: str, repo_root: Path, run=subprocess.run) -> Path`（tar のパス）。

- [ ] テスト: docstring の `uvicorn app.main:create_default_app --factory` → CMD に `--factory`・`--host 0.0.0.0` / `app = FastAPI(` から組み立て / requirements.txt なら `-r requirements.txt` / node + start → `npm start` / 判定不可 → CMD なし・has_cmd False・警告 / 既存 Dockerfile は上書きしない / build_image が `docker build`・`docker save` を引数リストで呼び、`.gitignore` を作る / docker 失敗で PortfolioError
- [ ] 失敗確認 → 実装 → 成功 → コミット

### Task 5: フロントエンドの登録（R2-1, R2-2）

**Files:** Create `importer/frontend.py`, Test `tests/test_frontend.py`

**Interfaces:** Consumes `Frontend`, `copy_tree`。Produces `register_frontend(frontend: Frontend, slug: str, repo_root: Path) -> tuple[bool, list[str]]`（登録したか、警告）。

- [ ] テスト: apps/<slug> へコピーし apps.json に追記 / apps.json がなければ作成 / 既存スラッグは重複登録しない / apps/<slug> 既存ならコピーしない / kind=None なら何もしない
- [ ] 失敗確認 → 実装 → 成功 → コミット

### Task 6: 掲載 md（R4-1〜R4-4）

**Files:** Create `importer/content.py`, Test `tests/test_content.py`

**Interfaces:** Produces `write_portfolio_md(slug: str, project: Path, repo_root: Path, tags: list[str], app_url: str | None, today: date) -> tuple[Path | None, list[str]]`、`parse_frontmatter(text: str) -> tuple[dict, str]`。

- [ ] テスト: docs の title・tags・本文を使い先頭 h1 を除く / `url: ""` は入れない / README から title / どちらもなければスラッグ / app_url は http(s) のみ / 既存なら作らず警告 / 書き出した frontmatter がダブルクォート文字列
- [ ] 失敗確認 → 実装 → 成功 → コミット

### Task 7: コマンド本体（R5-1, N1, N3）

**Files:** Create `importer/cli.py`、Modify `add_portfolio.py`, Test `tests/test_cli.py`

**Interfaces:** Produces `main(argv: list[str], repo_root: Path, run=subprocess.run, today=None) -> int`。

- [ ] テスト: 外部プロジェクト（vite フロント + python バックエンド）で全成果物が作られ JSON が出る / `--site-url https://ex.com` で url が `https://ex.com/apps/<slug>/` / `--build-image` で run が呼ばれる・CMD なしなら呼ばれない / エラー時は終了コード 1
- [ ] 失敗確認 → 実装 → 成功 → コミット

### Task 8: portfolio-site の配信（R2-3, R2-4）

**Files:** Create `portfolio-site/apps/apps.json`、`scripts/apps-manifest.mjs`、`scripts/build-apps.mjs`、`docs/apps.md`, Modify `package.json`（`build:apps`）、`buildspec.yml`、`eslint.config.mjs`、`tsconfig.json`、`infra/template.yaml`（Output `AppsBaseUrl`）、`infra/README.md`、`tests/infra-template.test.ts`、`docs/projects.md`, Test `tests/apps-manifest.test.ts`

**Interfaces:** Produces `validateManifest(data: unknown): {slug, outputDir, buildArgs}[]`。

- [ ] テスト: 正常 / 不正スラッグ / 重複 / `../x`・絶対パスの outputDir / `;` を含む引数 / apps が配列でない → 例外。infra テストの Outputs に `AppsBaseUrl`
- [ ] 失敗確認 → 実装 → `npm test`・`npm run lint` 成功 → コミット

### Task 9: スキル（R5-1, R5-2）

**Files:** Create `.claude/skills/add-portfolio/SKILL.md`、`portfolios/portfolio-importer/README.md`, Modify `docs/skills.md`

- [ ] design.md「スキル」節の手順で SKILL.md を書く。docs/skills.md の一覧に追加
- [ ] 既存の `portfolios/spotify-billboard-playlist` でコマンドを実行し、成功指標どおりか確認（生成物はこのブランチでは採用するか判断して報告）
- [ ] コミット
