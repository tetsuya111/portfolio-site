# batch（汎用バッチ）

特定のサイトに依存しない、静的サイト向けの汎用バッチです。Python 3.12 の標準ライブラリだけで動きます（差分デプロイだけ boto3 を使います）。

| スクリプト | 内容 |
|---|---|
| [generate_it_articles.py](generate_it_articles.py) | IT ニュースの記事を Perplexity API で自動作成し、frontmatter つきの Markdown としてフォルダに書き出す |
| [deploy_diff.py](deploy_diff.py) | ビルド成果物のフォルダと S3 を内容（MD5）で比べ、変わったファイルだけを送り、そのパスだけ CloudFront のキャッシュを無効化する |

portfolio-site での使い方（定期実行・AWS の設定）は [../../portfolio-site/docs/it-articles.md](../../portfolio-site/docs/it-articles.md) を参照してください。

## generate_it_articles.py（IT 記事の自動作成）

```bash
PERPLEXITY_API_KEY=pplx-... python generate_it_articles.py --out-dir <書き出し先> [--existing-dir <dir>]... [--count N] [--tag TAG]...
```

| 引数・環境変数 | 既定 | 内容 |
|---|---|---|
| `--out-dir` | （必須） | 記事の書き出し先。ここにある記事は重複判定・ファイル名の重なり判定にも使う |
| `--existing-dir` | なし | 重複判定に加えるフォルダ（複数可） |
| `--count` | `IT_ARTICLES_PER_RUN`、なければ 5 | 作る記事の数。1〜10 に丸める |
| `--tag` | `IT ニュース` | 全記事に付けるタグ（複数可） |
| `PERPLEXITY_API_KEY` | （必須） | Perplexity の API キー。表示・ログには出さない |
| `PERPLEXITY_MODEL` | `sonar` | 使うモデル |

処理の流れ:

1. 題材選定: 直近の重要な IT ニュースの候補を最大 15 件集め、重要度（1〜10）の高い順に並べる。既存記事の `sourceUrl` と同じ出典（`https` への統一・`www.`・`#`・`utm_*`・末尾 `/` の違いは同じとみなす）は除く。
2. 記事執筆: 重要度の高い題材から順に、本文・参考情報・用語解説を書かせる。失敗した題材は次の候補で補う（試すのは `--count` の 2 倍まで）。参考リンクは、モデルが書いた URL ではなく、API が検索で実際に参照した URL（`search_results`、なければ `citations`）から作る。
3. 書き出し: `<out-dir>/YYYY-MM-DD-<slug>.md`（日付は日本時間）。同じ名前があれば `-2`、`-3` … を付け、既存のファイルは上書きしない。

出力する Markdown:

```markdown
---
title: "記事のタイトル"
date: "2026-11-14"
tags: ["IT ニュース", "Astro"]
description: "1〜2 文の要約"
sourceUrl: "https://..."
generator: "perplexity/sonar"
---

> この記事は AI（perplexity/sonar）が 2026-11-14 に自動で作成しました。…

（本文）

## 参考情報
## 用語解説
## 参考リンク
```

- frontmatter の値は JSON の形式で書く（YAML としても正しく、記号のエスケープが確実なため）。
- LLM の出力は信用せず、コード以外の `<` を `&lt;` にし、`http(s)`・`#` 以外のリンク（`javascript:` など）を文字だけにし、本文の `#` 見出しを `##` に下げる（Markdown の生 HTML によるスクリプトの埋め込みを防ぐ）。
- 参考情報・用語解説・参考リンクのいずれかが無い記事、応答が JSON でない記事は書き出さずに失敗として数える。

終了コード: `0` 成功（題材がなく 0 本でも成功）／`1` API キーなし・題材選定の失敗・1本も書けず失敗があった／`2` 引数の誤り。

## deploy_diff.py（MD5 差分デプロイ）

```bash
pip install "boto3==1.35.0"
DIST_DIR=dist BUCKET=<バケット> [PREFIX=<バケット内のパス>] [DISTRIBUTION_ID=<ID>] [DELETE_REMOVED=true] [DRY_RUN=true] python deploy_diff.py
```

- S3 の ETag（`put_object` で1回で送ったオブジェクトは MD5 と一致する）とローカルの MD5 を比べ、違うものだけを `put_object` で送る。
- `_astro/` 以下（ファイル名に内容のハッシュが付くアセット）は長期キャッシュにし、無効化しない。それ以外は `max-age=0, must-revalidate`。
- 無効化するパスは、変わったページの `/<path>/index.html` と `/<path>/`。100 件を超えたら `/*` の1件にまとめる。`PREFIX` はキーには付け、無効化のパスには付けない（CloudFront が `PREFIX` をドメイン直下として配信する前提）。
- 既定ではフォルダに無いオブジェクトを削除しない（`DELETE_REMOVED=true` で削除）。`DRY_RUN=true` なら送らずに差分だけ表示する。

## テスト

```bash
npm test   # = python -m unittest discover -s tests -t .（実際の API・AWS は呼ばない）
```
