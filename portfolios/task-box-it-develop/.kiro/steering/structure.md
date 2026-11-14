---
inclusion: always
---

# ディレクトリ構成

```
task_box_it_develop/
├── backend/     # Django REST Framework API（アプリは backend/ 直下: accounts / agents / chat / summaries）
├── frontend/    # Next.js (App Router) フロントエンド（ページは src/app/、コンポーネントは src/components/、共通処理は src/lib/）
├── line_bot/    # LINE BOTサーバー（FastAPI。app/ 配下に line / features / agents、worker は RQ）
├── docs/        # 各アプリの詳細ドキュメント（backend.md / frontend.md / line-bot.md）
├── memo/        # 構想メモ、エージェントのプロンプト草案、見積もり基準（memo/雑多な/ITビジネス/タスク百葉箱/ 配下）
├── logs/        # 作業ログ
├── .kiro/
│   ├── steering/  # 常時参照される永続的なプロジェクトコンテキスト（このファイルを含む）
│   ├── specs/     # 機能ごとの requirements.md / design.md / tasks.md
│   └── hooks/     # イベント駆動の自動化の一覧（実体は .claude/settings.json のhooks設定）
└── CLAUDE.md    # 索引。詳細は docs/ と .kiro/ を参照
```

## memo/ の内容

`memo/雑多な/ITビジネス/タスク百葉箱/` 配下がこのプロダクトの一次情報。

- `アイデア.md` — 事業構想（需要、競合、強み、ターゲティング、見積もりの基準）
- `エージェント/` — エージェント一覧と、ヒアリングbot・要件サマリー作成エージェントのプロンプト草案、チャットのサポート機能の案
- `見積もり/` — 相場見積もり・自分見積もりのエージェントのプロンプト草案、エンドポイント単価のランク表
- `アプリ開発/webサイト作成.md` — アプリ本体の要件と技術選定（hearing-chat-site のspecの元）
- `TODO.md` — 残作業

## 配置の指針

- バックエンドの新規Djangoアプリは `backend/<app_name>/` に作成し、既存のアプリの構成（`models.py` / `services.py` / `views.py` / `urls.py` / `tests.py`）に倣う。
- フロントエンドの新規ページは `frontend/src/app/` 配下（App Router）に追加する。`page.tsx` からは `default` 以外を export せず、共有する関数は `src/lib/` に置く。
- 新機能に着手する際は、まず `.kiro/specs/<feature-slug>/` に requirements → design → tasks を作成してから実装に入る（詳細は [.kiro/specs/README.md](../specs/README.md)）。
- `memo/` は構想段階の草案置き場。仕様として確定した内容は `.kiro/specs/` や `.kiro/steering/` に反映し、実装は `memo/` ではなくそちらを正とする。エージェントの初期プロンプトは `backend/agents/seed_prompts/` にコピーしてあり、`memo/` の草案を直しても自動では反映されない。
- ドキュメントの詳細情報は `docs/` に一本化し、`.kiro/steering/` や `CLAUDE.md` からはリンクのみ行う（重複させない）。
