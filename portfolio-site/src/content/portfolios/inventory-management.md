---
title: "在庫管理システム（Next.js + FastAPI）"
tags:
  - "React"
  - "Next.js"
  - "TypeScript"
  - "Python"
  - "FastAPI"
date: 2026-11-17
---

商品マスタの管理、入庫・出庫の記録、在庫数の集計とダッシュボードを備えた在庫管理システムです。ポートフォリオとして、**設計（要件定義・設計書・タスク分解）から実装・テストまで**を一通り示すことを目的に作りました。

- **フロントエンド**: Next.js 16（App Router・静的出力）/ React 19 / TypeScript
- **バックエンド**: FastAPI / SQLAlchemy 2.0 / Alembic / Pydantic v2 / SQLite
- **認証**: JWT（HS256 のアクセストークン、Bearer）。権限は管理者（admin）と一般（staff）の2区分
- **テスト**: pytest（API の結合テスト・並行出庫のテスト）/ Vitest + Testing Library

## 主な機能

| 機能 | 内容 |
|---|---|
| ログイン・ログアウト | ユーザーごとに JWT を発行。トークン切れ・無効化されたユーザーは自動でログイン画面へ |
| ユーザー管理（管理者） | ユーザーの登録（権限区分つき）と一覧 |
| 商品マスタ | 登録・一覧（検索）・編集・削除（管理者のみ、論理削除で履歴は残る） |
| 入出庫の記録 | 入庫・出庫を登録し在庫数を増減。在庫を超える出庫は拒否 |
| 入出庫履歴 | 商品・区分・期間で絞り込み、ページ送り |
| 在庫一覧 | 商品ごとの在庫数、発注点以下の「在庫が少ない」表示、在庫数で並び替え |
| ダッシュボード | 集計値、在庫数上位10商品の棒グラフ、在庫が少ない商品、直近の入出庫 |

### 設計上のポイント

- **在庫数の整合性**: 出庫は `UPDATE products SET stock = stock - :q WHERE id = :id AND stock >= :q` の1文で「在庫が足りるか」の判定と減算を同時に行い、記録の INSERT と同じトランザクションで確定します。読んでから書く処理がないため、同時に出庫が来ても在庫がマイナスになりません（DB の CHECK 制約 `stock >= 0` も併用）。スレッドで同時に出庫するテストで確認しています。
- **認可は DB の値を正とする**: トークンの検証後に DB からユーザーを引き直すため、無効化や権限変更がすぐに反映されます。
- **本番の安全装置**: `APP_ENV=production` で JWT の秘密鍵が未設定・32文字未満なら起動を中止します。
- **静的出力の SPA**: フロントエンドは `next build` で静的ファイルになり、このサイトの `/apps/inventory-management/` 配下で配信しています。

## ディレクトリ構成

```
inventory-management/
├── package.json            # npm test / lint / build（backend と frontend をまとめて実行）
├── docker-compose.yml      # バックエンドをコンテナで起動（開発・動作確認用）
├── .env.example            # 環境変数の例
├── backend/                # FastAPI（app/ がアプリ、alembic/ がマイグレーション、tests/ がテスト）
├── frontend/               # Next.js（src/app が画面、src/lib が API クライアント・認証）
├── scripts/                # backend の venv を使ってコマンドを実行する補助スクリプト
├── docs/
│   ├── architecture.md     # 構成図・ER 図・API・画面一覧
│   └── specs/              # requirements.md・design.md・tasks.md
└── logs/                   # 作業ログ
```

## セットアップ

前提: Python 3.12 以上、Node.js 20 以上。

```bash
# バックエンド
cd backend
python -m venv .venv
.venv/bin/pip install -e ".[dev]"        # Windows は .venv\Scripts\pip
cd ..
npm run db:migrate                        # DB（backend/inventory.db）を作成
node scripts/run-backend.mjs -m app.cli create-admin --username admin   # パスワードは入力を求められる
# 対話できない環境では環境変数で渡す: INVENTORY_ADMIN_PASSWORD='<8文字以上>' node scripts/run-backend.mjs -m app.cli create-admin --username admin

# フロントエンド
npm --prefix frontend install
```

デモ用のデータ（ユーザー・商品・入出庫）を入れる場合:

```bash
node scripts/run-backend.mjs -m app.cli seed-demo
```

デモ用のアカウントは `demo-admin`（管理者）・`demo-staff`（一般）で、パスワードはどちらも `demo-password` です。本番環境（`APP_ENV` が `development`・`test` 以外）では、`--allow-production` を付けない限り作成しません。**公開デモとして作る場合は、管理者の権限が誰にでも使える点に注意してください。**

## 起動

```bash
npm run dev:backend     # http://localhost:8000（API 仕様は http://localhost:8000/docs）
npm run dev:frontend    # http://localhost:3000
```

Docker でバックエンドを起動する場合:

```bash
docker compose up -d --build
docker compose exec backend python -m app.cli seed-demo
```

DB は名前付きボリューム `inventory-data`（コンテナ内の `/data`）に置かれ、コンテナを作り直しても残ります。

## テスト・lint・ビルド

```bash
npm test          # backend の pytest → frontend の Vitest
npm run lint      # ruff（check・format）→ ESLint・tsc
npm run build     # frontend を静的出力（frontend/out/）
```

## 環境変数

バックエンドは `backend/.env`、フロントエンドは `frontend/.env.local` に書けます（例はリポジトリの `.env.example`）。

| 変数 | 既定 | 説明 |
|---|---|---|
| `APP_ENV` | `development` | `development`・`test` 以外は本番とみなし、JWT の秘密鍵の強度を起動時に確認する |
| `DATABASE_URL` | `sqlite:///./inventory.db` | SQLAlchemy の接続文字列 |
| `JWT_SECRET` | 開発用の固定値 | 本番では32文字以上のランダムな値を必ず指定する |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | アクセストークンの有効期限（分） |
| `CORS_ORIGINS` | `http://localhost:3000` | 許可するフロントエンドのオリジン（カンマ区切り） |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | フロントエンドから呼ぶ API の URL（ビルド時に埋め込み） |

## API

詳細は起動後の `/docs`（Swagger UI）を参照してください。ログイン以外は `Authorization: Bearer <token>` が必要です。

| メソッド・パス | 権限 | 内容 |
|---|---|---|
| `POST /auth/login` | なし | ログイン（JWT 発行。フォーム形式） |
| `POST /auth/register` | 管理者 | ユーザー登録 |
| `GET /users/me` | ログイン | ログインユーザー情報 |
| `GET /users` | 管理者 | ユーザー一覧 |
| `GET /products?q=&include_deleted=` | ログイン | 商品一覧（検索。`include_deleted=true` で削除済みも） |
| `POST /products` | ログイン | 商品登録 |
| `GET /products/{id}` | ログイン | 商品詳細 |
| `PUT /products/{id}` | ログイン | 商品更新（在庫数は変えない） |
| `DELETE /products/{id}` | 管理者 | 商品削除（論理削除） |
| `POST /inventory/in` | ログイン | 入庫の記録 |
| `POST /inventory/out` | ログイン | 出庫の記録（在庫不足は 409） |
| `GET /inventory/history` | ログイン | 入出庫履歴（`product_id`・`type`・`date_from`・`date_to`・`utc_offset_minutes`・`limit`・`offset`） |
| `GET /inventory/summary` | ログイン | 在庫数の集計 |

## 設計資料

- `docs/architecture.md` — 構成図・ER 図・在庫の整合性・画面一覧
- `docs/specs/requirements.md` — 要件定義（前提と仮定・受け入れ基準・Non-Goals）
- `docs/specs/design.md` — 設計（API・データモデル・検討した代替案・横断的関心事）
- `docs/specs/tasks.md` — 実装タスク

## 既知の制約

- 履歴の期間の絞り込みは、画面を開いた時点のブラウザの UTC からの差で日付を解釈します。夏時間（DST）のある地域で切り替えをまたぐ期間を指定すると、境界が最大1時間ずれます（日本時間には影響しません）。
- `docker compose` の設定は開発用で、`127.0.0.1:8000` でだけ待ち受けます。

## スコープ外（将来の拡張候補）

細かい権限管理、在庫アラートの通知、CSV エクスポート、入出庫記録の訂正・取消、リフレッシュトークン。詳細は要件定義（`docs/specs/requirements.md`）の Non-Goals に記載しています。
