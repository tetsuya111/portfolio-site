---
inclusion: always
---

# ディレクトリ構成

```
adult_feed_site/
├── backend/                  # Django REST Framework API
│   ├── api/                  # models.py / serializers.py / views.py / urls.py / admin.py / migrations/
│   ├── config/               # Django プロジェクト設定（settings.py / urls.py / wsgi.py）
│   ├── tools/                # 収集・加工バッチ（management/commands/ 配下）
│   ├── media/                # ダウンロードした動画・画像（videos/ images/。gitignore対象）
│   ├── logs/access.log       # アクセスログ（api.access ロガー）
│   └── readme.md
├── frontend/                 # Next.js (App Router)
│   ├── src/app/              # ページ。各ページは page.tsx のみを置く
│   ├── src/components/       # 状態を持つクライアントコンポーネント・共通UI
│   ├── src/lib/              # api.ts（APIクライアント）/ auth.ts（JWT・Turnstile状態）
│   ├── src/middleware.ts     # アクセスログ出力・Turnstile有効判定
│   └── readme.md
├── logs/                     # 作業ログ（CLAUDE.md の「作業ログ」を参照）
├── .kiro/
│   ├── steering/             # 常時参照される永続的なプロジェクトコンテキスト（このファイルを含む）
│   ├── specs/                # 機能ごとの requirements.md / design.md / tasks.md
│   └── hooks/                # イベント駆動の自動化の一覧（実体は .claude/settings.json）
├── start.sh                  # バックエンド・フロントエンドをまとめて起動
├── readme.md                 # リポジトリ全体の概要
└── CLAUDE.md                 # 索引。詳細は各readmeと .kiro/ を参照
```

## 主なページとコンポーネントの対応

`src/app/<path>/page.tsx` は対応する `src/components/<Name>Client.tsx` を読み込むだけにする。

| ページ | クライアントコンポーネント |
| --- | --- |
| `/feed`, `/article/[id]` | `FeedPlayer.tsx` |
| `/search` | `SearchPageClient.tsx` |
| `/tags` | `TagsPageClient.tsx` |
| `/articles` | `ArticlesPageClient.tsx` |
| `/article/create` | `ArticleCreateClient.tsx` |
| `/blog-parts` | `BlogPartsCreateClient.tsx` |
| `/click-stats` | `ClickStatsClient.tsx` |
| `/contact` | `ContactClient.tsx` |
| `/profile/[username]` | `ProfilePageClient.tsx` |
| `/following/[username]` | `FollowingPageClient.tsx` |
| `/users` | `UsersPageClient.tsx` |

全ページ共通で `layout.tsx` が `ThemeRegistry`（MUIダークテーマ）、`Navbar`、`TurnstileGuard` を差し込む。

## 配置の指針

- **バックエンドのAPI追加**: モデルは `api/models.py`、シリアライザは `api/serializers.py`、ビューは `api/views.py`、ルーティングは `api/urls.py` に追記する。新しいDjangoアプリは原則作らない（現状は `api` と `tools` のみ）。パスは末尾スラッシュを付ける。
- **収集・加工バッチの追加**: `backend/tools/management/commands/<command_name>.py` に1コマンド1ファイルで追加し、既存コマンドの引数の付け方（`-n/--number`、`--dry-run`、`--force` など）に倣う。追加したら [backend/tools/readme.md](../../backend/tools/readme.md) の一覧と詳細を更新する。
- **フロントエンドのページ追加**: `src/app/<path>/page.tsx` を作り、実装は `src/components/<Name>Client.tsx` に置く。ナビゲーションに出す場合は `Navbar.tsx` も更新する。
- **APIクライアント**: 新しいエンドポイントを呼ぶ処理は `src/lib/api.ts` に関数として追加する。コンポーネント内で `axios` / `fetch` を直接使わない。
- **メディアファイル**: `backend/media/videos/` と `backend/media/images/` 以外に保存しない（gitignore対象）。S3へ移す場合は `move_content_to_s3` を使い、`Content.path` を `s3://` 形式にする。
- **新機能に着手する際**: まず `.kiro/specs/<feature-slug>/` に requirements → design → tasks を作成してから実装に入る（詳細は [.kiro/specs/README.md](../specs/README.md)）。
- **ドキュメント**: 詳細情報は各 `readme.md` に一本化し、`.kiro/steering/` や `CLAUDE.md` からはリンクのみ行う（重複させない）。
