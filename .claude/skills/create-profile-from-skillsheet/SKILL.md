---
name: create-profile-from-skillsheet
description: スキルシート（スプレッドシート・Excel・Word・テキスト・HTML）の内容から、portfolio-site の自己紹介 profile.md を作成して置き換える。/create-profile-from-skillsheet <ファイルのパス | URL> で明示起動のみ。
disable-model-invocation: true
---

# create-profile-from-skillsheet

引数（`$ARGUMENTS`）で指定したスキルシートを読み、`portfolio-site/src/content/profile/profile.md` を作り直す。読み込みと検証・置き換えは Python 製コマンド [portfolios/skillsheet-profile](../../../portfolios/skillsheet-profile/README.md) が行い、このスキルは項目の読み取りと文章の作成を受け持つ。スキルシートは人によって書式が違うため、コマンドは列やセルを解釈しない。読み取りはこのセッションで行う。

## 確認のルール

基本は確認せずに進める。次の操作だけは、実行する直前に AskUserQuestion で yes/no を確認する。

| 操作 | no の場合 |
|---|---|
| URL（`http://`・`https://`）を `extract` に渡す（外部サイトへのアクセス） | 取得せず、ファイルをダウンロードしてパスを指定するよう案内して終了する |

リポジトリ外のローカルファイルでも、コマンドは**読むだけ**なので確認しない。

## 手順

1. **引数の確認**: `$ARGUMENTS` からファイルのパスか URL を取り出す。なければ直前の会話・開いているファイルから推定する。推定できなければ、何も書き換えずに理由を報告して終了する。
2. **読み込み**（リポジトリのルートで実行）:
   ```bash
   python portfolios/skillsheet-profile/skillsheet_profile.py extract "<パス | URL>"
   ```
   - 標準出力が抽出したテキスト。xlsx は `# シート: <名前>` ごとに、セルがタブ区切りで並ぶ。
   - 終了コード 1 なら、標準エラーの理由（非公開のスプレッドシート・未対応の形式など）をそのまま報告して終了する。案内に従ったファイルの指定し直しはユーザーに任せる。
   - 出力が空・スキルシートと思えない内容（ログイン画面など）なら、置き換えずに報告して終了する。
3. **既存の profile.md を読む**: `portfolio-site/src/content/profile/profile.md` を Read する（スキルシートにない項目の引き継ぎ元）。
4. **下書きの作成**: [references/profile-prompt.md](references/profile-prompt.md) を Read し、その指示に従って、抽出テキストと既存の profile.md から profile.md の全文を作る。下書きはファイルに保存しない。
5. **検証と置き換え**: 下書きを標準入力で渡す（ヒアドキュメントの区切りは本文に現れない文字列にする）。
   ```bash
   python portfolios/skillsheet-profile/skillsheet_profile.py apply - <<'PROFILE_EOF'
   <下書きの全文>
   PROFILE_EOF
   ```
   - 成功すると `{"target": ..., "replaced": true}` が出る。
   - 終了コード 1 なら、標準エラーに並んだ理由に沿って下書きを直し、再実行する（最大2回）。それでも通らなければ、置き換えずに理由と下書きを報告して終了する。
6. **作業ログ**: CLAUDE.md の規則に従い `logs/<yyyymmdd_hhMMss>_content_profile-from-skillsheet.md` に、何を（元にしたスキルシートの種類・置き換えたファイル）・なぜを書く。スキルシートの内容や個人情報は書かない。
7. **報告**: 次を箇条書きで示す。コミットはしない（ユーザーに任せる）。
   - 置き換えたファイル（`git diff portfolio-site/src/content/profile/profile.md` で差分を確認できること）
   - スキルシートから読み取れず、既存の profile.md の値を引き継いだ項目
   - 落とした個人情報の種類（電話番号・住所など。値そのものは書かない）
   - 自分で判断して書いた箇所（肩書きの言い換え・経歴のまとめ方など）

## よくある間違い

| 間違い | 正しい扱い |
|---|---|
| 抽出テキストや下書きをリポジトリ内のファイルに保存する | 保存しない。抽出は標準出力、下書きは標準入力で受け渡す |
| Write ツールで profile.md を直接書き換える | 書き換えない。必ず `apply` で検証してから置き換える |
| スキルシートにない GitHub の URL・経歴を推測で足す | 足さない。既存の profile.md の値を引き継ぐか、項目を省く |
| 取引先企業の実名・電話番号などをそのまま載せる | 載せない（公開サイトに出る）。プロンプトの除外規則に従う |
| 非公開スプレッドシートの取得に失敗したので、別の方法で認証を試みる | 試みない。xlsx か csv でダウンロードして指定するよう案内する |
