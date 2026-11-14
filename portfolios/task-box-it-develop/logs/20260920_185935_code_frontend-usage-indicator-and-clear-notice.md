# 対話画面に今日の残りの割合を表示し、クリアの確認に保持期間の案内を加えた

対象: タスク4・5

## 何を

- `frontend/src/components/chat/UsageIndicator.tsx`（新規）: 「今日の残り ○%」を操作エリアの先頭に表示する。残り10%未満は色に加えて「（少なくなっています）」のテキストでも知らせる。管理者（`unlimited`）は「今日の残り 制限なし」。取得できていないときは何も表示しない。`role="status"` 付き。
- `frontend/src/lib/types.ts`: `Usage` に `remaining_percent` と `unlimited` を追加し、`limit` を `number | null` にした。
- `frontend/src/components/chat/ChatScreen.tsx`: 状態を `limitReached: boolean` から `usage: Usage | null` に変更。429を受けた直後は再取得を待たずに残り0%として反映する。更新の契機は従来の `refreshUsage()`（初期ロードと各操作の完了時）のまま。
- `frontend/src/components/chat/dialogs.tsx`: 「クリア」の確認に「1か月お話がないと、自動的に消えます」を追記。
- `chat.test.tsx` にテストを追加（割合の表示、残りわずか、上限到達、管理者、取得失敗、クリアの案内）。

## なぜ

相談の途中で突然使えなくなると依頼者が戸惑うため、残りを常に見える形にした。表示は割合のみとし、トークン数の実数と専門用語は出していない（依頼者はITに疎い非エンジニアを想定）。

## 確認

`npm run lint` と `npx vitest run`（22件）がパス。
