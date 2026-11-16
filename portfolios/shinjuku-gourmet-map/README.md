# 新宿グルメマップ

新宿のおすすめのお店を、ジャンルを切り替えながら Google マップで探せるWebアプリです（ポートフォリオ用）。

- 画面上部のジャンルボタン（ラーメン・カフェ・居酒屋など）を押すと、同じ地図上にそのジャンルのお店のピンが表示されます。
- ピンを押すと、店名・住所・評価・営業時間・電話番号・Webサイト・「Googleマップで開く」リンクが表示されます。
- ジャンルは設定ファイルに手で書いて追加・変更します（閲覧者が自由に検索する機能はありません）。

仕様: [要件定義](docs/specs/requirements.md) ／ [設計](docs/specs/design.md) ／ [タスク](docs/specs/tasks.md)

## 技術構成

| 用途 | 使用技術 |
| --- | --- |
| 言語・ビルド | TypeScript、Vite（UIフレームワークなし） |
| 地図・ピン | Google Maps JavaScript API（Advanced Marker） |
| 店舗検索・詳細 | Places API (New) の Text Search |
| テスト | Vitest + jsdom（Google Maps はフェイクに差し替えて検証） |
| Lint | ESLint（typescript-eslint）、`tsc --noEmit` |

サーバーは持たず、ビルドした静的ファイルを配信するだけで動きます。

## セットアップ

Node.js 22 以上が必要です。

```bash
cd portfolios/shinjuku-gourmet-map
npm install
cp env.template .env   # .env に APIキーを書く（次の節を参照）
npm run dev            # http://localhost:5173 を開く
```

APIキーを設定しなくても画面は開き、設定方法の案内が表示されます。

## APIキーの設定

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作り、請求先アカウントを設定します（無料枠の利用にも必要です）。
2. 「APIとサービス」→「ライブラリ」で次の2つを有効にします。
   - Maps JavaScript API
   - Places API (New)
3. 「認証情報」→「認証情報を作成」→「APIキー」でキーを作り、`.env` の `VITE_GOOGLE_MAPS_API_KEY` に貼り付けます。
4. （任意）「Google Maps Platform」→「マップ管理」で JavaScript 用の Map ID を作り、`VITE_GOOGLE_MAPS_MAP_ID` に設定します。空の場合は Google のデモ用ID（`DEMO_MAP_ID`）を使います。

`.env` は Git の管理対象外です。リポジトリには値が空の `env.template` だけを置いています。

### キーの悪用を防ぐ設定（必須）

地図をブラウザで表示する仕組み上、APIキーはビルドした JavaScript に含まれ、閲覧者から見える状態になります。`.env` で管理するのは「リポジトリに載せない」ためで、公開後の悪用は Google Cloud 側の制限で防ぎます。公開前に、作成したキーの編集画面で必ず次を設定してください。

| 設定 | 内容 |
| --- | --- |
| アプリケーションの制限 | 「ウェブサイト」を選び、公開先URL（例: `https://<ユーザー名>.github.io/*`）と `http://localhost:5173/*` だけを許可する |
| API の制限 | 「キーを制限」を選び、Maps JavaScript API と Places API (New) だけを許可する |
| 1日あたりの上限 | 「APIとサービス」→ 各APIの「割り当てとシステム上限」で、1日のリクエスト数に上限を設定する（次の節を参照） |

あわせて、請求先アカウントで「予算とアラート」を設定しておくと、想定外の利用にすぐ気づけます。

## 費用（ランニングコストを0円に保つために）

Google Maps Platform には SKU（課金単位）ごとに毎月の無料利用枠があります。執筆時点の目安は次のとおりです。最新の情報は必ず[公式の料金ページ](https://developers.google.com/maps/billing-and-pricing/pricing)で確認してください。

| このアプリでの利用 | SKU | 毎月の無料枠（目安） |
| --- | --- | --- |
| 地図の表示（ページを開くたび1回） | Dynamic Maps | 10,000回 |
| ジャンルの検索（評価・営業時間・電話・Webサイトを取得） | Text Search Enterprise | 1,000回 |

費用を抑えるため、このアプリは次のようにしています。

- 1回の検索で取得するのは最大20件。
- 同じジャンルを選び直しても、ページを開いている間は再検索しない（メモリにキャッシュ）。

それでも無料枠を超えないよう、1日あたりの上限を「月の無料枠 ÷ 31」以下（例: Places API の Text Search は 1日30回、地図の表示は 1日300回）に設定してください。上限に達するとその日は検索できなくなりますが、課金は発生しません。

検索回数の枠を増やしたい場合は、[src/places/searchShops.ts](src/places/searchShops.ts) の `FIELDS` から評価・営業時間・電話番号・Webサイトを外すと、より無料枠の大きい SKU（Text Search Pro）で収まります（詳細パネルに出る項目は減ります）。

## ジャンル・エリアの変更

[src/config/map-config.json](src/config/map-config.json) を編集します。コードの変更は不要です。

```json
{
  "area": {
    "name": "新宿",
    "center": { "lat": 35.6896, "lng": 139.7006 },
    "radiusMeters": 1500,
    "zoom": 15
  },
  "genres": [
    { "id": "ramen", "label": "ラーメン", "query": "新宿 ラーメン", "icon": "🍜" },
    { "id": "gyoza", "label": "餃子", "query": "新宿 餃子 人気", "icon": "🥟" }
  ]
}
```

| 項目 | 説明 |
| --- | --- |
| `area.name` | 画面の説明文に表示するエリア名 |
| `area.center` | 地図の中心と検索範囲の中心（緯度・経度） |
| `area.radiusMeters` | 検索範囲の半径（メートル、1〜50000）。この範囲を囲む矩形の中だけを検索します |
| `area.zoom` | 地図の初期ズーム（1〜21） |
| `genres[].id` | ジャンルの識別子（英小文字・数字・ハイフン、重複不可） |
| `genres[].label` | ボタンに表示する名前 |
| `genres[].query` | Google に投げる検索語。「新宿 ラーメン 老舗」のように具体的にすると、おすすめを絞り込めます |
| `genres[].icon` | 任意。ボタンに添える絵文字 |

ボタンは書いた順に並び、ページを開いたときは先頭のジャンルが選ばれます。書き方に誤りがあると、画面に原因の項目が表示されます。

## コマンド

| コマンド | 内容 |
| --- | --- |
| `npm run dev` | 開発サーバーを起動 |
| `npm test` | 単体テストを実行 |
| `npm run lint` | ESLint と型チェック |
| `npm run build` | 型チェックのうえ `dist/` に本番用ファイルを出力 |
| `npm run preview` | ビルド結果をローカルで確認 |

## デプロイ

`npm run build` で `dist/` に静的ファイルができます。GitHub Pages・Netlify・Vercel など無料の静的ホスティングにそのまま置けます（相対パスで出力しているので、サブパスにも置けます）。

- APIキーはビルド時に埋め込まれます。CI でビルドする場合は、`VITE_GOOGLE_MAPS_API_KEY` をホスティングサービスの環境変数（シークレット）に設定してください。
- 公開URLを、APIキーの「ウェブサイト」制限に追加するのを忘れないでください。

## ディレクトリ構成

```
src/
  main.ts            起動処理（設定・APIキー・地図の読み込みと部品の配線）
  app.ts             ジャンル選択 → 検索 → ピン → 詳細の状態管理
  env.ts             .env から APIキー・Map ID を読む
  config/            ジャンル・エリアの設定ファイルと検証
  maps/              Google Maps の読み込み・ピン表示・最小の型定義
  places/            店舗検索・キャッシュ・店舗データ型
  ui/                ジャンルボタン・状態表示・詳細パネル
docs/specs/          要件定義・設計・タスク
```
