---
title: このポートフォリオサイト
tags:
  - Astro
  - Tailwind CSS
  - AWS
url: https://example.com/
date: 2026-11-13
---

## 概要

Astro と Tailwind CSS で作った静的サイトです。自己紹介・ポートフォリオ・記事を md ファイルで管理し、S3 と CloudFront で配信しています。

## 工夫した点

- 記事は md ファイルを置くだけで追加できる
- `main` への push で CodeBuild がテストとデプロイを行う
