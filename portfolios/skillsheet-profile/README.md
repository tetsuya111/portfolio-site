# skillsheet-profile

スキルシートからポートフォリオサイトの自己紹介（`portfolio-site/src/content/profile/profile.md`）を作るためのコマンド。Claude Code のスキル [/create-profile-from-skillsheet](../../.claude/skills/create-profile-from-skillsheet/SKILL.md) から呼び出す。Python 3.12 の標準ライブラリだけで動く（追加のインストール不要）。

スキルシートの書式は人によって違うため、このコマンドは列やセルを解釈しない。行うのは「テキストにする（`extract`）」と「下書きを検証して置き換える（`apply`）」だけで、項目の読み取りと文章の作成はスキル（Claude のセッション）が行う。

## 使い方

リポジトリのルートで実行する。

```bash
# スキルシートをテキストにして標準出力に出す
python portfolios/skillsheet-profile/skillsheet_profile.py extract <ファイルのパス | URL>

# 下書きを検証し、profile.md を置き換える（- なら標準入力から読む）
python portfolios/skillsheet-profile/skillsheet_profile.py apply <下書きのパス | -> [--target <パス>]
```

エラー時は理由を標準エラーに出し、終了コード 1 で終わる（`apply` は置き換えない）。

## extract が読める形式

| 形式 | 読み方 |
|---|---|
| `.txt`・`.md`・`.csv`・`.tsv` | そのままテキストとして読む（UTF-8・UTF-8（BOM 付き）・Shift_JIS） |
| `.html`・`.htm` | `script`・`style` を除いた本文。表はセルをタブ区切り |
| `.xlsx`・`.xlsm` | 全シートを `# シート: <名前>` の見出しごとに、セルをタブ区切りで出す |
| `.docx` | 段落と表の行 |
| Google スプレッドシートの URL | 「リンクを知っている全員」が閲覧できるシートだけ。xlsx でエクスポートして読む。非公開のシートは OAuth に対応していないため、xlsx か csv でダウンロードしてファイルを指定する |
| その他の http(s) URL | HTML として読む |

- `.xls`・`.doc`・`.ods`・PDF は読めない（xlsx・docx・csv で保存し直す）。
- ファイル・応答・xlsx/docx の展開後のサイズは 20MB まで。URL のタイムアウトは 30 秒。

## apply の検証

portfolio-site の `profileSchema`（[schemas.ts](../../portfolio-site/src/lib/schemas.ts)）と同じ規則を Python で確かめる。**スキーマを変えたら [skillsheet/profile.py](skillsheet/profile.py) も直すこと。**

- 先頭に `---` で囲んだ frontmatter があり、`name`・`role` が空でない文字列。`summary` は文字列。`links` の各要素に `label` と http(s) の `url` がある。
- frontmatter はトップレベルの `key: value` と `links` の並びだけを解釈する。YAML で文字列以外（数値・真偽値・日付）になる値や、`: ` を含む値はクォートを求める。
- 本文に見出し `## 自己紹介`・`## 経歴`・`## スキル` がある。
- 合格したら、同じディレクトリの一時ファイルに UTF-8・LF で書き、差し替える（途中で失敗しても元のファイルは壊れない）。

## 開発

```bash
cd portfolios/skillsheet-profile
npm test      # python -m unittest
npm run lint  # 構文チェック（python -m compileall）
```

設計: `docs/specs/create-profile-from-skillsheet/`（ローカルのみ。git 管理外）
