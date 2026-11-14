# AWS 環境のセットアップ手順（infra/template.yaml）

[../infra/template.yaml](../infra/template.yaml) を使って、ポートフォリオサイトの配信基盤（S3・CloudFront・ACM・Route 53）と CI/CD（CodeBuild）を AWS 上に初めて作るまでの手順。上から順に進めれば、`DeployBranch` への push でサイトが自動でデプロイされる状態になる。

作成されるリソース・パラメーターの詳細・CI の動き・スタックの削除・トラブルシューティングは [../infra/README.md](../infra/README.md) を参照。

## 全体の流れ

| # | 手順 | 目安の時間 |
|---|---|---|
| 1 | [AWS CLI の準備](#1-aws-cli-の準備) | 数分 |
| 2 | [Route 53 ホストゾーンの準備](#2-route-53-ホストゾーンの準備) | 数分〜（ネームサーバー変更の反映に最大48時間） |
| 3 | [CodeBuild への GitHub 認証情報の登録](#3-codebuild-への-github-認証情報の登録) | 数分 |
| 4 | [パラメーターの決定](#4-パラメーターの決定) | 数分 |
| 5 | [テンプレートの検証](#5-テンプレートの検証) | 数分 |
| 6 | [スタックの作成](#6-スタックの作成) | 数分〜数十分 |
| 7 | [作成結果の確認](#7-作成結果の確認) | 数分 |
| 8 | [初回デプロイ](#8-初回デプロイ) | 数分 |

コマンドはすべて `portfolio-site/` ディレクトリで実行する。リージョンは**すべて us-east-1**（CloudFront 用の ACM 証明書は us-east-1 でしか作れないため。ほかのリージョンではテンプレートの `Rules` により作成前に失敗する）。

## 1. AWS CLI の準備

1. AWS CLI v2 をインストールする（[公式手順](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)）。
2. 認証情報を設定し、操作するアカウントが正しいことを確認する。

   ```bash
   aws configure            # または aws configure sso
   aws sts get-caller-identity
   ```

3. 使う IAM ユーザー／ロールに、次のサービスのリソースを作成・更新できる権限があることを確認する。
   - CloudFormation・S3・CloudFront・ACM・Route 53・CodeBuild・CloudWatch Logs・IAM（ロールを作るため。デプロイ時に `CAPABILITY_IAM` を指定する）

## 2. Route 53 ホストゾーンの準備

サイトのドメイン（例 `portfolio.example.com`）を含むホストゾーンが必要。テンプレートはホストゾーン自体は作らず、証明書の検証レコードとエイリアスレコードだけを追加する。

1. 既存のホストゾーンを確認する。

   ```bash
   aws route53 list-hosted-zones-by-name --dns-name example.com \
     --query "HostedZones[].{Name:Name,Id:Id,Private:Config.PrivateZone}" --output table
   ```

   - `Id` の `/hostedzone/` より後ろ（例 `Z0123456789ABCDEFGHIJ`）が、後で使う `HostedZoneId`。
   - **パブリック**ゾーン（`Private` が `False`）を使うこと。

2. ない場合は作成する。

   ```bash
   aws route53 create-hosted-zone --name example.com --caller-reference "$(date +%s)"
   ```

3. ドメインを Route 53 以外のレジストラで取得している場合は、レジストラ側のネームサーバーを、このホストゾーンの NS レコード（4つ）に変更する。

   ```bash
   aws route53 get-hosted-zone --id <HostedZoneId> --query "DelegationSet.NameServers"
   ```

4. 委任が反映されたことを確認する（Route 53 の NS が返ればよい）。**反映前にスタックを作ると、証明書の DNS 検証が終わらず作成が止まる。**

   ```bash
   nslookup -type=NS example.com
   ```

## 3. CodeBuild への GitHub 認証情報の登録

CodeBuild が GitHub に Webhook を作り、PR にビルド結果を表示するために必要。認証情報はテンプレートに含めず、事前に **us-east-1 で**登録する（認証情報はリージョンごと）。

### 方法 A: コンソールから接続する

CodeBuild コンソール（us-east-1）→「ビルドプロジェクトを作成する」→ ソースプロバイダーで GitHub を選び「GitHub に接続」する。接続が済んだらプロジェクトは作らずに画面を閉じてよい。

### 方法 B: 個人用アクセストークンを登録する

1. GitHub の Settings → Developer settings → Personal access tokens でトークンを作る。
   - classic トークンの場合のスコープ: `repo`、`admin:repo_hook`
   - fine-grained トークンを使う場合の権限は [AWS のドキュメント](https://docs.aws.amazon.com/codebuild/latest/userguide/access-tokens-github.html) を参照。
2. CodeBuild に登録する。

   ```bash
   aws codebuild import-source-credentials --region us-east-1 \
     --server-type GITHUB --auth-type PERSONAL_ACCESS_TOKEN --token <トークン>
   ```

3. 登録されたことを確認する。

   ```bash
   aws codebuild list-source-credentials --region us-east-1
   ```

トークンはリポジトリ・テンプレート・ログに残さないこと（シェルの履歴にも残るため、実行後に履歴から消すか、方法 A を使う）。

## 4. パラメーターの決定

次の値を用意する（各項目の詳細は [../infra/README.md のパラメーター](../infra/README.md#パラメーター)）。

| パラメーター | 例 | 決め方 |
|---|---|---|
| `DomainName` | `portfolio.example.com` | 手順 2 のホストゾーン内の名前。小文字のみ |
| `HostedZoneId` | `Z0123456789ABCDEFGHIJ` | 手順 2 で確認した ID |
| `GitHubRepoUrl` | `https://github.com/<owner>/<repo>.git` | このリポジトリの HTTPS URL |
| `DeployBranch` | `main` | 本番へデプロイするブランチ（省略時・空なら任意のブランチへの push でデプロイする） |

スタック名は以下では `portfolio-site` とする。CodeBuild のプロジェクト名（`<スタック名>-test`・`<スタック名>-deploy`）やロググループ名に使われる。

## 5. テンプレートの検証

```bash
# 構文チェック
aws cloudformation validate-template --region us-east-1 --template-body file://infra/template.yaml

# テンプレートの設定値のテスト（infra-template.test.ts を含む）
npm test
```

## 6. スタックの作成

パラメーターの値は `infra/parameters.json` に書いて読み込む（git の管理外。各パラメーターの意味は [../infra/README.md](../infra/README.md#パラメーター)）。初回だけ例をコピーして値を書き換える。

```bash
cp infra/parameters.example.json infra/parameters.json
```

Windows では、AWS CLI が日本語を含む `template.yaml` を cp932 で読もうとしてエラーになるため、先に `AWS_CLI_FILE_ENCODING=UTF-8` を設定する（PowerShell: `$env:AWS_CLI_FILE_ENCODING = "UTF-8"`、Git Bash: `export AWS_CLI_FILE_ENCODING=UTF-8`）。

1. （任意）変更セットだけを作って、作成されるリソースを確認する。

   ```bash
   aws cloudformation deploy --region us-east-1 --stack-name portfolio-site --template-file infra/template.yaml --capabilities CAPABILITY_IAM --parameter-overrides file://infra/parameters.json --no-execute-changeset
   ```

   出力に表示される `aws cloudformation describe-change-set ...` を実行すると内容を確認できる。問題なければ、コンソールから変更セットを実行するか、次の手順に進む。

   > **注意:** 表示される `describe-change-set` のコマンドには `--region` が含まれない。そのまま実行すると既定のリージョン（`aws configure` で設定したもの）を探しにいき、変更セットがあっても `ChangeSetNotFound` になる。`--region us-east-1` を付けて実行するか、作業前に `$env:AWS_DEFAULT_REGION = "us-east-1"`（Git Bash: `export AWS_DEFAULT_REGION=us-east-1`）を設定しておく。
   >
   > ```bash
   > aws cloudformation describe-change-set --region us-east-1 --change-set-name <表示された変更セットの ARN> \
   >   --query "Changes[].ResourceChange.[Action,LogicalResourceId,ResourceType]" --output table
   > ```
   >
   > 変更セットの状態は `aws cloudformation list-change-sets --region us-east-1 --stack-name portfolio-site` で確認できる（`CREATE_COMPLETE` なら作成できている）。CLI から実行する場合は `aws cloudformation execute-change-set --region us-east-1 --change-set-name <ARN>` を使う。
   >
   > 初回は、変更セットを実行するまでスタックが `REVIEW_IN_PROGRESS` のまま残る。この状態ではリソースは何も作られていない。やり直したいときは `aws cloudformation delete-stack --region us-east-1 --stack-name portfolio-site` で削除してよい。

2. スタックを作成する（上のコマンドから `--no-execute-changeset` を外す）。2回目以降は同じコマンドで更新になる。

   ```bash
   aws cloudformation deploy \
     --region us-east-1 \
     --stack-name portfolio-site \
     --template-file infra/template.yaml \
     --capabilities CAPABILITY_IAM \
     --parameter-overrides file://infra/parameters.json
   ```

   証明書の DNS 検証と CloudFront の配置に時間がかかるため、初回は数分〜数十分かかる。

3. 進み具合や失敗の原因は、スタックのイベントで確認する。

   ```bash
   aws cloudformation describe-stack-events --region us-east-1 --stack-name portfolio-site \
     --query "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]" \
     --output table
   ```

   初回作成に失敗するとスタックは `ROLLBACK_COMPLETE` になり、そのままでは更新できない。原因を直したら `aws cloudformation delete-stack` で削除してから作り直す（作成済みの S3 バケットは残るため、不要なら手動で削除する）。

## 7. 作成結果の確認

1. 出力を確認する。

   ```bash
   aws cloudformation describe-stacks --region us-east-1 --stack-name portfolio-site \
     --query "Stacks[0].Outputs" --output table
   ```

   | 出力 | 内容 |
   |---|---|
   | `SiteUrl` | サイトの URL（`https://<DomainName>/`） |
   | `BucketName` | サイトのファイルを置く S3 バケット名 |
   | `DistributionId` | CloudFront ディストリビューション ID |
   | `AppsBaseUrl` | ポートフォリオのフロントエンドの配信先（`https://<DomainName>/apps/`）。各アプリは `<AppsBaseUrl><スラッグ>/`（[apps.md](apps.md)） |

2. CodeBuild のプロジェクトが2つできていることを確認する。

   ```bash
   aws codebuild batch-get-projects --region us-east-1 \
     --names portfolio-site-test portfolio-site-deploy \
     --query "projects[].{Name:name,Webhook:webhook.url}" --output table
   ```

3. GitHub のリポジトリの Settings → Webhooks に、CodeBuild の Webhook が2つ（テスト用・デプロイ用）登録されていることを確認する。

この時点ではバケットが空なので、`SiteUrl` を開いてもページは表示されない（エラーになる）。

## 8. 初回デプロイ

`portfolio-site/` 配下を変更するコミットを `DeployBranch` に push すると、`portfolio-site-deploy` がテスト・lint・ビルドを行い、成功したら S3 に同期して CloudFront のキャッシュを無効化する。CodeBuild コンソールからの手動開始ではデプロイされない（Webhook の PUSH イベントのときだけデプロイする。詳細は [../infra/README.md の CI / デプロイ](../infra/README.md#ci--デプロイ)）。

すぐに反映したい場合は、ローカルでビルドして直接同期してもよい。

```bash
npm run build
npm run build:apps     # apps/apps.json に登録したフロントエンドがある場合
aws s3 sync dist "s3://<BucketName>" --delete
aws cloudfront create-invalidation --distribution-id <DistributionId> --paths "/*"
```

デプロイ後、次を確認する。

- [ ] `SiteUrl` をブラウザで開くとトップページが表示される
- [ ] `http://` で開くと `https://` にリダイレクトされる
- [ ] 存在しないパス（例 `/no-such-page/`）で 404 ページが表示される
- [ ] `portfolio-site/` 配下を変更した PR を作ると、`portfolio-site-test` のビルド結果が PR に表示される

うまくいかない場合は [../infra/README.md のうまくいかないとき](../infra/README.md#うまくいかないとき) を参照。
