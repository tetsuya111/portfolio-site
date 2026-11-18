# 在庫管理システムの構成

要件・設計の詳細は [specs/requirements.md](specs/requirements.md)・[specs/design.md](specs/design.md) を参照。ここでは全体像を図でまとめる。

## システム構成

```mermaid
flowchart LR
  subgraph Browser[ブラウザ]
    UI[Next.js 静的 SPA<br/>React 19 / TypeScript]
  end
  subgraph Server[API サーバー（Docker）]
    API[FastAPI<br/>routers → services]
    ORM[SQLAlchemy 2.0]
  end
  DB[(SQLite<br/>/data/inventory.db)]
  UI -- "fetch + Authorization: Bearer JWT" --> API
  API --> ORM --> DB
  MIG[Alembic] -. "起動時に upgrade head" .-> DB
```

- フロントエンドは `next build` の静的出力。S3 などのサブパス配下で配信でき、API の URL はビルド時の環境変数で切り替える。
- バックエンドは `routers/`（入出力・HTTP のエラー）と `services/`（在庫の増減などの業務ロジック）に分け、業務ロジックを HTTP から独立してテストできるようにしている。

## ER 図

```mermaid
erDiagram
  users ||--o{ stock_movements : "操作する"
  products ||--o{ stock_movements : "対象"
  users {
    int id PK
    string username UK "3〜50文字"
    string password_hash "bcrypt"
    string role "admin / staff / visitor"
    bool is_active
    datetime created_at
  }
  products {
    int id PK
    string sku UK "削除済みを含めて一意"
    string name
    string category
    string unit
    int unit_price
    int reorder_point "発注点"
    int stock "CHECK >= 0"
    string description
    bool is_deleted "論理削除"
    datetime created_at
    datetime updated_at
  }
  stock_movements {
    int id PK
    int product_id FK
    int user_id FK
    string type "in / out"
    int quantity "CHECK > 0"
    int stock_after "記録後の在庫数"
    string note
    datetime created_at "インデックス"
  }
```

## 在庫の増減（整合性の担保）

```mermaid
sequenceDiagram
  participant C as クライアント
  participant A as FastAPI
  participant D as DB
  C->>A: POST /inventory/out {product_id, quantity}
  A->>D: UPDATE products SET stock = stock - q<br/>WHERE id = :id AND is_deleted = false AND stock >= q
  alt 1行更新
    A->>D: INSERT stock_movements（stock_after を保存）
    A->>D: COMMIT
    A-->>C: 201 記録
  else 0行更新
    A->>D: ROLLBACK
    A-->>C: 409 在庫不足（商品がなければ 404）
  end
```

判定と減算が1文の UPDATE にまとまっているため、同時に出庫が来ても DB が1件ずつ適用し、在庫が足りない方は0行更新になる。`tests/test_inventory_concurrency.py` で8スレッドの同時出庫を行い、在庫がマイナスにならないことを確認している。

## 認証・認可

```mermaid
sequenceDiagram
  participant B as ブラウザ
  participant A as FastAPI
  B->>A: POST /auth/login（username, password）
  A-->>B: access_token（JWT: sub, role, iat, exp）
  B->>A: GET /products（Authorization: Bearer）
  A->>A: 署名・期限を検証 → DB からユーザーを取得（無効なら 401）
  A-->>B: 200
  Note over B: 401 を受け取ったらトークンを捨ててログイン画面へ
```

| 操作 | 管理者 | 一般 |
|---|---|---|
| 商品の登録・更新、入出庫の記録、各種参照 | ○ | ○ |
| 商品の削除 | ○ | × (403) |
| ユーザーの登録・一覧 | ○ | × (403) |

## 画面一覧

| パス | 画面 |
|---|---|
| `/login` | ログイン |
| `/` | ダッシュボード（集計・棒グラフ・在庫が少ない商品・直近の入出庫） |
| `/products` | 商品一覧（検索・編集・削除） |
| `/products/new` | 商品登録 |
| `/products/edit?id=` | 商品編集（静的出力のため ID はクエリで指定） |
| `/inventory` | 在庫一覧（並び替え・在庫が少ない表示） |
| `/inventory/record` | 入出庫の登録 |
| `/inventory/history` | 入出庫履歴（絞り込み・ページ送り） |
| `/users` | ユーザー管理（管理者のみ） |

## テスト

| 対象 | 内容 |
|---|---|
| `backend/tests/` | API の正常系・異常系（401・403・404・409・422）、マイグレーション、並行出庫、集計と入出庫の合計の一致、CLI、OpenAPI の網羅 |
| `frontend/src/**/*.test.ts(x)` | API クライアント、認証コンテキスト、商品フォーム、棒グラフ、整形・並び替え・集計の関数 |
