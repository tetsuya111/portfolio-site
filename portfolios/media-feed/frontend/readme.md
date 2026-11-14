# frontend

Next.js + MUI を使った Web クライアント。バックエンド API からコンテンツを取得して表示する。

---

## 起動

```bash
cd website/frontend
npm install
npm run dev
```

http://localhost:3000

---

## ディレクトリ構成

```
frontend/
├── src/
│   ├── app/                      ページ (App Router)
│   │   ├── feed/                 コンテンツフィード
│   │   ├── search/               コンテンツ検索
│   │   ├── tags/                 タグ一覧
│   │   ├── articles/             記事一覧
│   │   ├── article/
│   │   │   ├── create/           記事作成
│   │   │   └── [id]/             記事詳細
│   │   ├── profile/[username]/   ユーザープロフィール・ブックマーク
│   │   ├── following/[username]/ フォロー中ユーザー一覧
│   │   ├── users/                ユーザー一覧
│   │   └── login/                ログイン・ユーザー登録
│   ├── components/               共通 UI コンポーネント
│   │   ├── Navbar.tsx            ナビゲーションバー
│   │   ├── FeedPlayer.tsx        フィード再生コンポーネント
│   │   ├── SearchPageClient.tsx
│   │   ├── TagsPageClient.tsx
│   │   ├── ArticlesPageClient.tsx
│   │   ├── ArticleCreateClient.tsx
│   │   ├── ArticlePageClient.tsx
│   │   ├── ProfilePageClient.tsx
│   │   ├── FollowingPageClient.tsx
│   │   ├── UsersPageClient.tsx
│   │   └── ThemeRegistry.tsx     MUI ダークテーマ
│   └── lib/
│       ├── api.ts                API クライアント (axios)
│       └── auth.ts               認証ユーティリティ (JWT / localStorage)
├── package.json
└── next.config.ts
```

---

## 主な画面

| パス | 説明 |
|---|---|
| `/feed` | コンテンツフィード (動画・画像のスワイプ表示) |
| `/search` | キーワード・タグ・タイプでコンテンツを検索 |
| `/tags` | タグ一覧 (件数順/名前順ソート、絞り込み検索) |
| `/articles` | 記事一覧 (グリッド表示、タイトル・タグで検索) |
| `/article/create` | 記事作成 (コンテンツ選択・タグ付け・サムネイル自動決定) |
| `/article/<id>` | 記事詳細フィード (記事コンテンツ + 関連コンテンツ) |
| `/profile/<username>` | ユーザープロフィール・ブックマーク一覧 |
| `/following/<username>` | フォロー中ユーザー一覧 |
| `/users` | ユーザー一覧 (説明文検索・フォロー機能) |
| `/login` | ログイン・ユーザー登録 |

---

## FeedPlayer の操作方法

| 操作 | 動作 |
|---|---|
| 上スワイプ / ↑キー / ホイールアップ | 前のシリーズへ |
| 下スワイプ / ↓キー / ホイールダウン | 次のシリーズへ |
| 左スワイプ / ←キー | 前のシリーズへ |
| 右スワイプ / →キー | 次のシリーズへ |
| 画面上部タップ | 元サイトを開く |
| 画面中央タップ | 再生/一時停止・コンテンツ一覧 |
| 画面下部タップ | コンテンツ情報表示 |

コンテンツタイプフィルタ: すべて / 動画 / 画像 / DMM動画 / DMM画像

---

## API クライアント (`src/lib/api.ts`)

- **ベース URL**: `NEXT_PUBLIC_API_URL` 環境変数 (デフォルト: `/api` — Next.js の rewrite でバックエンドに転送)
- JWT アクセストークンをリクエストヘッダに自動付与
- 401 エラー時にリフレッシュトークンでトークンを自動更新
- `getMediaUrl(content)` — ローカルファイルは `/api/contents/{id}/media/`、外部URLはそのまま返す

## 他ホストからのアクセス

フロントエンドは API 呼び出しにすべて相対パス (`/api/...`) を使用するため、  
別デバイスから `http://<サーバーIP>:3000` にアクセスしても通信が成立します。

バックエンドがフロントエンドと別マシンにある場合は、`BACKEND_URL` 環境変数を設定してください。

```bash
# フロントエンドと同一マシンでバックエンドを起動する場合 (デフォルト)
npm run dev

# バックエンドが別マシン (例: 192.168.1.50) にある場合
BACKEND_URL=http://192.168.1.50:8000 npm run dev
```

---

## 依存ライブラリ

| ライブラリ | 用途 |
|---|---|
| `Next.js 15` | React フレームワーク (App Router) |
| `React 19` | UI ライブラリ |
| `MUI v6` | UI コンポーネント (ダークテーマ) |
| `Swiper` | スライダー表示 |
| `axios` | API リクエスト・トークン管理 |
