# CLAUDE.md と .kiro/steering をタスク百葉箱向けに書き換え

## 何を行ったか

- `CLAUDE.md` を、別プロジェクト（community_sns）の内容からこのプロジェクト（タスク百葉箱）向けに書き換えた。
- `.kiro/steering/product.md` / `tech.md` / `structure.md` を同様に書き換えた。

## なぜ行ったか

- いずれも community_sns からコピーされた内容のままで、存在しない `backend/` / `frontend/` / `docs/` / `.github/` を前提にしていたため。
- 内容は `memo/雑多な/ITビジネス/タスク百葉箱/` 配下の構想メモ（アイデア.md、エージェントのプロンプト草案、アプリ開発/webサイト作成.md）を元にした。

## 主な変更点

- プロダクト概要・想定ユーザー・主要機能（構想）・要件サマリーの項目・見積もりの考え方を product.md に定義した。
- 技術スタックを「採用予定」として tech.md に記載した（DRF / Next.js / Claude / Voyage AI / RAG）。
- 現状のディレクトリ構成（`memo/` と `.kiro/` のみ）と未作成のディレクトリを structure.md で区別した。
- CLAUDE.md から存在しない `docs/*.md` へのリンクを外し、エージェントのプロンプトを扱う際の注意を追加した。

## 未対応

- `.kiro/specs/` 配下の community_sns 由来のspec（accounts、community-management など）、`.kiro/specs/README.md` の `docs/` へのリンク、`.kiro/hooks/README.md` のhook一覧は今回の対象外で、そのまま残っている。
