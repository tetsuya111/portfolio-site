# セキュリティニュースの自動作成（/security-news/）

AI（Perplexity）が最近公表された脆弱性・セキュリティ情報から記事を自動で作成し、`/security-news/`（一覧）と `/security-news/<スラッグ>/`（記事ページ）に掲載する仕組み。手で書いた記事（`/articles/`）・IT ニュース（`/it-news/`）とは並べない（`/articles/` からボタンでたどれる）。

仕組みのほとんどは [IT ニュースの自動作成](it-articles.md) と共通で、同じ定期実行（`<スタック名>-it-articles`）の中で、IT 記事を作ったあとに作成する。ここには違う点だけを書く。

## IT ニュースとの違い

| 項目 | セキュリティニュース | IT ニュース |
|---|---|---|
| 記事の置き場所 | `src/content/security-articles/`（コレクション `securityArticles`） | `src/content/it-articles/` |
| 正本（S3） | 記事バケットの `security-articles/` | 同じバケットの `it-articles/` |
| バッチ | `portfolios/batch/generate_security_articles.py` | `generate_it_articles.py` |
| 1回の本数 | `SecurityArticlesPerRun`（既定 3、0〜10。0 で作らない） | `ItArticlesPerRun`（既定 5） |
| 既定のタグ | `セキュリティ` | `IT ニュース` |
| 題材 | 直近 7 日に公表・更新された脆弱性・セキュリティインシデント | 直近の IT ニュース |
| 記事の構成 | 概要／脆弱性の詳細／具体的な対応方法／IT業界における経緯／関連技術／IT用語の解説／備考／参考リンク | 本文／参考情報／用語解説／参考リンク |

- 定期実行の間隔・ON/OFF・モデル・API キーは IT ニュースと共通（`ItArticlesScheduleExpression`・`ItArticlesScheduleState`・`PerplexityModel`・`PerplexityApiKeyParameterName`）。
- セキュリティ記事の作成に失敗しても（API のエラーなど）、IT 記事の保存・公開は続ける。ただし、スキーマを満たさない md があればビルドが失敗し、どちらも保存・公開しない（IT ニュースと同じ）。
- push のデプロイ（`buildspec.yml`）も、ビルドの前に `security-articles/` を取り込む。

## 有効にする

IT ニュースの[初期設定](it-articles.md#初期設定)を済ませれば、既定（1回 3 本）で作られる。本数を変える・止めるときは、`infra/parameters.json` の `SecurityArticlesPerRun` を変えてスタックを更新する。

## ローカルで試す

```bash
# リポジトリのルートで。記事は src/content/security-articles/ に書き出され、git には入らない
PERPLEXITY_API_KEY=pplx-... python portfolios/batch/generate_security_articles.py --out-dir portfolio-site/src/content/security-articles --count 1
cd portfolio-site && npm run dev   # http://localhost:4321/security-news/
```

## 記事を消す・直す

記事バケットの `security-articles/<ファイル名>.md` を削除・編集し、push のデプロイか定期実行を待つ（手順は [it-articles.md](it-articles.md#記事を消す直す) と同じ）。

## コストの目安（既定: 1日1回・3本の追加分）

- Perplexity `sonar`: 1日 4 回の呼び出し（題材選定 1 + 記事 3）の追加で、月数十円〜100 円前後の想定。
- CodeBuild: 1回 1〜2 分の増加（月 30〜60 分）。無料枠を超えた分で月 $0.3 程度まで。
