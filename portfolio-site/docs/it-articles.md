# IT ニュースの自動作成（/it-news/）

AI（Perplexity）が最新の IT ニュースから記事を自動で作成し、`/it-news/`（一覧）と `/it-news/<スラッグ>/`（記事ページ）に掲載する仕組み。手で書いた記事（`/articles/`・トップの新着欄）とは並べない。記事を作るバッチは、サイトに依存しない汎用の道具として [../../portfolios/batch/](../../portfolios/batch/README.md) に置いている。

## 流れ

```
EventBridge Scheduler（ItArticlesScheduleExpression、既定 rate(1 day)。ItArticlesScheduleState で ON/OFF）
  └─ CodeBuild <スタック名>-it-articles（buildspec.it-articles.yml、DeployBranch のコード）
       1. 過去の記事を取り込む   s3://<記事バケット>/it-articles/*.md → src/content/it-articles/
       2. 新しい記事を作る       portfolios/batch/generate_it_articles.py（既定 5 本）
       3. サイト全体をビルド     npm run test:build（スキーマ違反の md があればここで失敗）
       4. 成功したときだけ       記事を S3 に保存 → deploy_diff.py で MD5 が変わったファイルだけ配信用バケットへ送り、そのパスだけ無効化
```

- 記事の正本は S3 の記事バケット（`ItArticlesBucketName` の出力）。git には `src/content/it-articles/.gitkeep` だけを置き、`*.md` は `.gitignore` で除外している。
- push 時のデプロイ（`buildspec.yml`）も、ビルドの前に記事バケットから記事を取り込む（取り込まないと `s3 sync --delete` で公開中の記事のページが消える）。
- 定期実行と push のデプロイが同時に走ると、push 側の `s3 sync --delete` が、その間に公開された新しい記事のページを消すことがある（記事の md は S3 に保存済みなので、次の定期実行で自動的に戻る）。気になる場合は、定期実行の時刻（`cron(...)`）を push しない時間帯にする。
- 定期実行では `apps/` をビルドしないため、配信用バケットのファイルは削除しない。不要になったファイルの掃除は push 時のデプロイに任せる。

## 初期設定

1. Perplexity の API キーを SSM Parameter Store に SecureString で登録する（既定の `aws/ssm` キーで暗号化）。
   ```bash
   aws ssm put-parameter --region us-east-1 --name /portfolio-site/perplexity-api-key --type SecureString --value "<API キー>"
   ```
   dev スタックは別の名前（例 `/portfolio-site-dev/perplexity-api-key`）にし、`PerplexityApiKeyParameterName` で指定する。
2. `infra/parameters.json` に次を追記して（既定のままでよければ省略可）、スタックを更新する（[../infra/README.md](../infra/README.md)）。

   | 名前 | 既定 | 内容 |
   |---|---|---|
   | `ItArticlesScheduleExpression` | `rate(1 day)` | 実行間隔。`rate(...)` か `cron(...)`（タイムゾーンは Asia/Tokyo。例 `cron(0 6 * * ? *)` で毎日 6:00） |
   | `ItArticlesScheduleState` | `DISABLED` | `ENABLED` で定期実行を ON。API キーを登録してから ON にする |
   | `ItArticlesPerRun` | `5` | 1回で作る記事の数（1〜10） |
   | `PerplexityModel` | `sonar` | `sonar` か `sonar-pro` |
   | `PerplexityApiKeyParameterName` | `/portfolio-site/perplexity-api-key` | 手順 1 のパラメーター名 |

3. すぐに試すときは手動で実行する（プロジェクト名は `ItArticlesProjectName` の出力）。
   ```bash
   aws codebuild start-build --region us-east-1 --project-name <スタック名>-it-articles
   ```

## ローカルで試す

```bash
# リポジトリのルートで。記事は src/content/it-articles/ に書き出され、git には入らない
PERPLEXITY_API_KEY=pplx-... python portfolios/batch/generate_it_articles.py --out-dir portfolio-site/src/content/it-articles --count 1
cd portfolio-site && npm run dev   # http://localhost:4321/it-news/
```

## 記事を消す・直す

記事バケットの `it-articles/<ファイル名>.md` を削除・編集し、push のデプロイか定期実行を待つ（バージョニングが有効なので、誤って消しても 90 日以内なら戻せる）。削除した記事のページは、push 時のデプロイ（`--delete`）で配信用バケットからも消える。

## コストの目安（既定: 1日1回・5本）

- CodeBuild（general1.small）: 1回 4〜6 分 → 月 120〜180 分。無料枠（月 100 分）を超えた分で月 $0.1〜0.4 程度。
- Perplexity `sonar`: 1日 6 回の呼び出し（題材選定 1 + 記事 5）で、月 100 円前後の想定（記事の長さと検索の回数で変わる。料金は Perplexity の料金ページで確認する）。
- S3・EventBridge Scheduler・CloudWatch Logs は誤差。料金の異常は既存の AWS Budgets 通知で気づける。
