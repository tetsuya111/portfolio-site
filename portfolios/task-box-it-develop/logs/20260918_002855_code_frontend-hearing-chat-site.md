# フロントエンド（hearing-chat-site タスク2, 5, 16〜18）を実装

## 何を行ったか

- `frontend/` に Next.js 16（App Router）+ TypeScript + Tailwind CSS のプロジェクトを新規作成した。
- LP、ログイン（Google / 開発用）、対話画面（ストリーミング表示、テンプレ、5つのボタン、確認ダイアログ、確定フロー、クリアの確認、上限の表示、画面のイメージのプレビュー）、管理者画面（一覧・絞り込み・詳細・対応状況の変更）を実装した。
- Vitest + Testing Library を導入した。

## なぜ行ったか

`.kiro/specs/hearing-chat-site/tasks.md` の実装。

## 確認したこと

- `npm run test`（16件）、`npm run lint`、`npm run build` がすべて成功。
- 開発サーバーで `/` `/login` `/chat` `/admin/summaries` `/admin/summaries/1` が200で返ること。

## 未確認

- ブラウザでの目視確認（一連の操作、スマートフォンの画面幅）。

## 注意

- `vitest` 5 は `@types/node` 22 以上を要求し、`create-next-app` の既定（20）のままだと依存関係の解決に失敗するため、`@types/node` を22に上げた。
- Next.js のページ（`page.tsx`）は `default` 以外を export できないため、共有する関数は `src/lib/` に置いた。
