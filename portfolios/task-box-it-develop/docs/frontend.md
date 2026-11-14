# フロントエンド

Next.js（App Router）+ TypeScript + Tailwind CSS。仕様は [.kiro/specs/hearing-chat-site/](../.kiro/specs/hearing-chat-site/design.md) を参照。

Next.js は 16 系で、従来と異なる点がある。コードを書く前に `frontend/node_modules/next/dist/docs/` の該当ガイドを確認すること（`frontend/AGENTS.md` の指示）。

## セットアップ

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local    # 値を設定する
npm run dev
```

## コマンド

| コマンド | 内容 |
| --- | --- |
| `npm run dev` | 開発サーバー（既定は3000。変える場合は `npx next dev -p 3001`） |
| `npm run lint` | ESLint |
| `npm run test` | Vitest + Testing Library（1回実行）。`npm run test:watch` で監視 |
| `npm run build` | 本番ビルド（型チェックを含む） |

## 環境変数

`frontend/.env.local` に書く（`.env.example` が雛形）。

| 変数 | 内容 |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | バックエンドのオリジン（既定値 `http://localhost:8000`）。バックエンドの `CORS_ALLOWED_ORIGINS` と対で変える |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | GoogleのOAuthクライアントID。バックエンドの `GOOGLE_OAUTH_CLIENT_ID` と同じ値 |
| `NEXT_PUBLIC_ENABLE_DEV_LOGIN` | `true` にするとログイン画面に開発用ログインのボタンを出す。バックエンド側で `ALLOW_DEV_LOGIN=true` が必要。本番では設定しない |

## アーキテクチャ

| パス | 内容 |
| --- | --- |
| `src/app/` | ルート。`/`（LP）、`/login`、`/chat`、`/admin/summaries`、`/admin/summaries/[id]` |
| `src/components/AuthProvider.tsx` | ログイン状態のコンテキスト、`RequireAuth`（ルートの保護） |
| `src/components/chat/` | 対話画面。`ChatScreen` が状態を持ち、`MessageBubble` / `Composer` / `ActionBar` / `dialogs` / `UsageIndicator` / `HtmlMockPreview` は表示のみ |
| `src/lib/api.ts` | fetch のラッパー。401のとき1回だけトークンを再発行してやり直す。SSEの読み取り（`streamMessage`） |
| `src/lib/sse.ts` / `html-mock.ts` / `admin.ts` / `types.ts` | SSEのパーサー、「画面のイメージ」の切り出しとCSP、管理者画面の表示用、型 |

実装上の決まりごと:

- 状態管理のライブラリは使わない。Reactの状態とコンテキストで足りる範囲に留める。
- アクセストークンはメモリ（`api.ts` のモジュール変数）にのみ持つ。`localStorage` に保存しない。リフレッシュトークンはバックエンドが発行する httpOnly Cookie。
- `RequireAuth` は表示の制御であり、認可はバックエンドが行う。
- 依頼者由来の文字列の表示: 対話の本文は `react-markdown`（`rehype-raw` を入れない = 生のHTMLを解釈しない）、要件サマリーの確認と管理者画面の本文は `<pre>` のテキスト、「画面のイメージ」は `sandbox=""` の iframe + CSP（`HtmlMockPreview`）。`dangerouslySetInnerHTML` は使わない。
- 「AIによる自動的な見積もりです」などの注意書きはLLMに書かせず、`MessageBubble` が `metadata` を見て固定で付ける。
- 依頼者向けの文言には専門用語を使わない。ボタン名は requirements.md（ストーリー7 基準6）の表記どおりとする。
- 今日あとどれくらい使えるかは、`UsageIndicator` が操作エリアの先頭に「今日の残り ○%」と割合で表示する（`GET /api/me/` の `usage`）。トークン数の実数と専門用語は出さない。残り10%未満は色とテキストの両方で知らせ、上限のない管理者は「制限なし」と表示する。取得に失敗したときは表示しない。
- `src/app/**/page.tsx` からは `default` 以外を export しない（Next.js のページの制約）。共有したい関数は `src/lib/` に置く。
- スマートフォンの画面幅を基準にレイアウトする。
