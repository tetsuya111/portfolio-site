---
name: superpowers-create-from-design-to-pr
description: 設計ファイル作成→ブランチ作成→TDD実装→テストと/code-review-ocrによるレビュー→修正のループ→push・PR作成・PRへのレビューコメントまでを、superpowersのスキル群を使って確認なしで一気通貫に実行する。/superpowers-create-from-design-to-pr で起動する。
disable-model-invocation: true
---

# superpowers-create-from-design-to-pr

引数（`$ARGUMENTS`）の機能要望を、設計からPR作成まで**ユーザーに一度も質問せずに**進める。

## 無人実行ルール（superpowersの各スキルより優先する）

- AskUserQuestion ツールを使わない。「よろしいですか？」「どちらにしますか？」と書かない。ただし下記「必ず確認する操作」は例外。
- superpowersスキル内の「質問する／承認を待つ／選択肢を提示する」手順は、推奨案を自分で選んで進めることに置き換え、選んだ内容は最終報告に書く。
- `superpowers:finishing-a-development-branch` の「3つの選択肢を提示」は使わない。代わりに下記「6. 完了処理」を行う。
- 処理を続けられない障害（テスト基盤が壊れている、認証エラー等）に当たったら、質問ではなく**状況報告として**停止する。

## 必ず確認する操作（無人実行ルールの例外）

次の操作は、実行する直前に AskUserQuestion で yes/no を確認する。no ならその操作を行わず、可能なら代替手段で続け、不可能なら状況報告して停止する。

- このプロジェクト（リポジトリのルート）外のファイルを作成・修正・削除する（グローバル設定・`~/.claude/`・スクラッチパッド以外の一時領域など）
- 外部URLにアクセスする（WebFetch・WebSearch・curl、`npm install` 等のパッケージ取得を含む）

ただし、このスキルの手順として明記された次の通信は起動時点で承認済みとみなし、確認しない: `/code-review-ocr` によるレビュー、`git push`、`gh` による認証確認・PR作成・PRコメント。PR本文用の一時ファイルをスクラッチパッドに書くことも確認不要。

## 手順

### 1. ブランチ作成（ファイルを1つでも変更する前に行う）

```bash
git switch -c dev/feature/claude-superpowers/<修正内容の要約>
```

- `<修正内容の要約>` は英小文字kebab-case・5語以内（例: `add-top-page-hero`）。
- 同名ブランチが既にある場合は末尾に `-2`、`-3` … を付ける。
- 未コミットの変更がある場合も stash・破棄はしない（そのまま新ブランチへ持ち越す）。

### 2. 設計

[../superpowers-create-design/SKILL.md](../superpowers-create-design/SKILL.md) を Read で読み、その手順を引数そのままで実行して設計ファイル一式を作る（同スキルはモデルからの自動起動を無効化しているため、Skill ツールでは呼ばない）。完了後、設計ファイルと作業ログをコミットする。

### 3. 実装

tasks.md を上から順に実装する。

- 各タスクは `superpowers:test-driven-development` に従う（失敗するテスト→実装→テスト成功）。
- 独立したタスクが複数ある場合は `superpowers:subagent-driven-development` を使ってよい。
- 不具合に当たったら `superpowers:systematic-debugging` に従う。
- タスク単位でコミットする。CLAUDE.md の作業ログ規則に従い `logs/` にログも追加する。

### 4. 検証とレビュー（指摘がなくなるまで繰り返す）

1. `package.json` の `scripts` にある test・lint・build を実行する（存在するものだけ）。出力は失敗箇所のみ確認する（例: `| tail -40`）。
2. Skill ツールで `code-review-ocr` を引数 `--from <ベースブランチ> --to HEAD` 付きで呼び出す。これは明示起動として扱い、実行確認は行わない。
3. 指摘は `superpowers:receiving-code-review` に従い実コードで妥当性を確かめ、妥当なものだけ修正してコミットする。
4. テスト失敗・妥当な指摘が0件になったら次へ。**最大3周**で打ち切り、残った指摘は最終報告とPR本文に「未対応」として書く。

最後に `superpowers:verification-before-completion` に従い、テスト・lintを再実行して成功を出力で確認する。

### 5. GitHub連携の判定

次をすべて満たす場合のみ「6. 完了処理」を行う。満たさない場合はローカルのコミットまでで止め、理由を報告する。

- `git remote get-url origin` が github.com を指す
- `gh auth status` が成功する
- ベースブランチ（`main`、なければリモートのデフォルトブランチ）がリモートに存在する

### 6. 完了処理（GitHub連携時）

0. **秘密情報チェック（push前に必ず行う）**: `git diff --name-only <ベースブランチ>...HEAD` と `git diff <ベースブランチ>...HEAD` を確認し、次のいずれかがあれば push せずに状況報告して停止する。
   - 秘密情報を含みうるファイル（`.env*`、`*.pem`、`*.key`、`.npmrc`、`credentials*.json`、`set-ocr-env.bat` など）が差分に含まれる
   - APIキー・トークン・パスワードらしき値（`sk-`、`ghp_`、`AKIA`、`-----BEGIN ... PRIVATE KEY-----`、`password=` など）が追加行に含まれる

   見つけた値そのものは報告に書かず、ファイル名と行番号だけを示す。
1. `git push -u origin <ブランチ名>`
2. `gh pr create --base <ベースブランチ> --title "<要約>" --body-file <一時ファイル>`
   本文: 概要／要件・設計ファイルへのリンク／テスト結果／未対応の指摘。末尾にシステム指示の帰属表記を付ける。
3. 4-2 の最終回のOCRレビュー結果を要約し、`gh pr comment <PR番号> --body-file <一時ファイル>` でPRにコメントする。
4. PRのURLを報告する。

一時ファイルはスクラッチパッドに作る。force push・ベースブランチへの直接push・マージはしない。

## 最終報告に含めるもの

ブランチ名、PR URL（あれば）、自分で決めた仮定・判断、レビュー周回数と未対応の指摘。
