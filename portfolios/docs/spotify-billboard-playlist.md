---
title: Billboard → Spotify Playlist
tags:
  - Python
  - FastAPI
  - Next.js
  - React
  - TypeScript
  - SQLite
  - OAuth 2.0
  - Spotify Web API
  - スクレイピング
url: ""
---

# Billboard → Spotify Playlist

Billboard Hot 100 のチャートページのURLを入力すると、その週の100曲を収めた非公開プレイリストを自分の Spotify アカウントに作るWebアプリです。

## 解決する課題

洋楽チャートを Spotify で聴こうとすると、100曲を1曲ずつ検索してプレイリストに追加する手作業が必要になります。このアプリでは、URLを入力してボタンを押すだけで済みます（必要なのは初回の Spotify ログインだけです）。

## 主な機能

- **チャートの取得**: [ビルボード・データベース](https://billboard.mryogaku.com/) のトップページ（最新週）や、日付を指定したチャートページのURLを受け付けます。これらは同じ週の Hot 100 全順位ページに読み替えて、100曲の順位・曲名・アーティストを取り出します。同じサイトのほかのページも、同じ表の形で曲が並んでいれば使えます。
- **Spotify ログイン**: OAuth 2.0（Authorization Code フロー）でログインします。要求する権限は、非公開プレイリストの作成に必要な最小限だけです。
- **プレイリストの作成**: 曲を Spotify で検索し、チャート順のプレイリストを作ります。見つからなかった曲は飛ばし、完了画面に一覧で表示します。
- **まとめて取得するバッチ**: DBに登録された未処理のURLを、コマンドラインからまとめてスクレイピングできます。

## 構成

```
ブラウザ → Next.js ─（/api・/auth を転送）→ FastAPI ─┬→ ビルボード・データベース（スクレイピング）
                                                    ├→ Spotify Accounts / Web API
                                                    └→ SQLite（取得したURLと曲の一覧）
```

| 層 | 技術 |
|---|---|
| フロントエンド | Next.js 16 / React 19 / TypeScript |
| バックエンド | Python 3.12 / FastAPI / httpx / Beautiful Soup |
| データ | SQLite（標準の `sqlite3`） |
| テスト・品質 | pytest・vitest・Testing Library / ruff・ESLint・tsc |

## 技術的な工夫

- **トークンをブラウザに渡さない**: OAuth の処理とトークンの保持はバックエンドだけで行い、ブラウザには推測できないセッションID の Cookie（HttpOnly）だけを渡します。Next.js の rewrites でフロントエンドとバックエンドを同じオリジンに見せることで、CORS を設定せずに Cookie を使えるようにしました。
- **安全に配慮した入力の扱い**:
  - スクレイピング先は1つのホストに限定し、リダイレクトをたどりません。任意のURLを取りに行かせる攻撃（SSRF）を防ぐためです。
  - OAuth の `state` を照合し、POST リクエストでは送信元（Origin）を確かめます。あわせて Cookie を `SameSite=Lax` にし、CSRF を防いでいます。
  - 入力値の長さや件数は Pydantic で検証します。
- **壊れにくいスクレイピング**: 40曲分しかなく、JavaScript の中に HTML が埋め込まれたページは直接解析しません。どのURLも、100曲がそろった簡易表示のページに読み替えてから解析します。
- **曲を見つけやすくする検索と API 制限への対応**:
  - まず曲名と主アーティスト（Featuring などより前の部分）を指定して検索し、見つからなければ条件をゆるめて検索し直します。
  - 同時に送る検索は5件までにし、Spotify から「リクエストが多すぎる」（429）と返されたら指定された時間待って再試行します。トークンの期限が切れていたら自動で更新します。
- **社内プロキシなどがある環境でも動く**: HTTPS の証明書は OS の証明書ストアで検証します。ウイルス対策ソフトの HTTPS 検査など、独自のルート証明書が入った環境でも、検証を無効にせずに接続できます。
- **外部サービスを差し替えたテスト**: HTTP 通信はモックに、HTML は実ページを縮めたテスト用データに差し替えて、Spotify やスクレイピング先に接続しなくてもテストを実行できるようにしました。

## 開発の進め方

要件定義 → 設計 → タスク分解 → テスト駆動開発（TDD）の順に進め、Claude Code を使って設計からPR作成までを自動化しました。

## 前提・制約

- ローカル環境（`http://127.0.0.1`）で本人が使う前提です。本番環境へのデプロイや、複数ユーザーでの利用は対象外です。
- 開発モードの Spotify アプリは、Developer Dashboard に登録したユーザーしか使えません。

## 関連資料

- セットアップ・起動方法: [spotify-billboard-playlist/README.md](../spotify-billboard-playlist/README.md)
- 要件・設計・タスク: [docs/specs/spotify-billboard-playlist/](../../docs/specs/spotify-billboard-playlist/)
