# website

各サイトから収集した動画・画像コンテンツを管理・閲覧するWebアプリケーション。

---

## 構成

```
website/
├── backend/    Django REST Framework ベースの API サーバー
├── frontend/   Next.js ベースの Web クライアント
└── start.sh    バックエンド・フロントエンドをまとめて起動するスクリプト
```

詳細は各ディレクトリの readme を参照。

---

## 起動

```bash
cd website
bash start.sh
```

| サービス | URL |
|---|---|
| バックエンド API | http://localhost:8000 |
| フロントエンド | http://localhost:3000 |

---

## 機能概要

### コンテンツ管理
- 複数サイトから収集した動画・画像の保存・一覧表示
- タグによる絞り込み・検索
- シリーズ（関連コンテンツのグルーピング）管理

### ユーザー機能
- ユーザー登録・ログイン (JWT 認証)
- ブックマーク・フォロー・コメント

### 記事機能
- 収集したコンテンツをまとめた記事の作成・閲覧
- 記事タグ・サムネイル自動生成

### ブログパーツ
- `/api/blog-parts/` で記事一覧の埋め込みHTML を生成
- `make_blog_parts` バッチでHTMLファイルとして書き出し可能

### バッチ処理
- 各サイトからコンテンツを自動収集するバッチコマンド群
- 詳細: [`backend/tools/readme.md`](backend/tools/readme.md)
