---
title: "IT ニュース自動作成"
description: "最新の IT ニュースを AI（Perplexity）が毎日自動で集めて重要度で選び、出典リンクと用語解説つきの記事にして、このサイトの「IT ニュース」に掲載する仕組み。サイト内の小さな機能として動いている。"
tags:
  - "Python"
  - "Perplexity API"
  - "AWS CodeBuild"
  - "EventBridge Scheduler"
  - "Astro"
url: "/it-news/"
date: 2026-11-14
---

最新の IT ニュースを AI（Perplexity）が毎日自動で集めて重要度で選び、出典リンクと用語解説つきの記事にして、このサイトの「IT ニュース」に掲載する仕組み。サイト内の小さな機能として動いている。

## 仕組み

1. EventBridge Scheduler が既定で1日1回、CodeBuild を起動する（間隔・ON/OFF・1回の本数はパラメーターで変更できる）。
2. CodeBuild は、これまでに作った記事を S3 から取り込んだあと、記事作成バッチ（Python）を実行する。
   - 1段目: Perplexity で直近の IT ニュースの候補を集め、重要度の高い順に選ぶ（取り上げ済みの出典は除く）。
   - 2段目: 題材ごとに、本文・参考情報・用語解説を書かせる。参考リンクは、モデルが書いた URL ではなく、Perplexity が検索で実際に参照した URL から作る。
3. サイト全体を Astro でビルドし、成功したら記事の md を S3 に保存する（失敗したら保存も公開もしない）。
4. 内容（MD5）が変わったファイルだけを配信用の S3 に送り、そのページだけ CloudFront のキャッシュを無効化する。

## 構成

| 場所 | 内容 |
| --- | --- |
| `portfolios/batch/` | 汎用の記事作成バッチと差分デプロイのスクリプト（Python 標準ライブラリ + boto3） |
| `portfolio-site/src/content/it-articles/` | 自動作成の記事（正本は S3。ビルドのたびに取り込む） |
| `portfolio-site/src/pages/it-news/` | 一覧と記事ページ |
| `portfolio-site/infra/template.yaml` | スケジューラ・CodeBuild・記事保存用バケット（CloudFormation） |

## 工夫した点

- LLM の出力は信用せず、HTML や `javascript:` リンクを無害化してから Markdown にする。
- API キーは SSM Parameter Store から実行時に渡し、リポジトリ・テンプレート・ログに残さない。
- 既定（1日1回・5本）で AWS の追加料金が月 $1 未満に収まるようにした。
