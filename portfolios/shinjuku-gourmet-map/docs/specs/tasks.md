# タスク: 新宿グルメマップ（shinjuku-gourmet-map）

要件: [requirements.md](requirements.md) ／ 設計: [design.md](design.md)

すべてのパスは `portfolios/shinjuku-gourmet-map/` からの相対パス。各タスクは「失敗するテストを書く → 実行して失敗を確認 → 実装 → テスト成功を確認 → コミット」の順に行う。確認コマンドはこのディレクトリで実行する。

## T1. プロジェクトの土台（NFR-8, FR-5.2）

- [ ] `package.json` に scripts（`dev` / `test` = `vitest run` / `lint` = `eslint . && tsc --noEmit` / `build` = `tsc --noEmit && vite build`）と devDependencies（vite, vitest, jsdom, typescript, eslint, @eslint/js, typescript-eslint, globals）を定義
- [ ] `tsconfig.json`（strict）、`vite.config.ts`（Vitest の environment = jsdom）、`eslint.config.js`、`.gitignore`（`node_modules`, `dist`, `.env`, `.env.*`）
- [ ] `src/smoke.test.ts` で `1 + 1 === 2` を確認し、仕組みが動くことを見たら削除
- 確認: `npm test && npm run lint`

## T2. 設定ファイルと検証（FR-4.1, FR-4.2, FR-1.1）

- [ ] `src/config/parseMapConfig.test.ts`: 正常系（型付きで返る）、ジャンル0件、id重複、id形式不正、label/query空、lat/lng範囲外、radius・zoom範囲外、複数違反をまとめて報告、の各テスト
- [ ] `src/config/parseMapConfig.ts`: `parseMapConfig(raw: unknown): MapConfig`、`ConfigError`
- [ ] `src/config/map-config.json`: 新宿駅中心・半径1500m・ジャンル5件（ラーメン・カフェ・居酒屋・寿司・カレー）
- [ ] 同梱の `map-config.json` が検証を通るテストを追加
- 確認: `npx vitest run src/config`

## T3. 環境変数の読み込み（FR-5.1, FR-5.3）

- [ ] `src/env.test.ts`: キーあり、キーが空・空白のみ・未定義で `null`、Map ID 未設定で `DEMO_MAP_ID`
- [ ] `src/env.ts`: `readApiSettings(env): ApiSettings | null`
- [ ] `env.template`（`VITE_GOOGLE_MAPS_API_KEY=` と `VITE_GOOGLE_MAPS_MAP_ID=`、値は空）、`src/vite-env.d.ts`
- 確認: `npx vitest run src/env.test.ts`

## T4. Google Maps の読み込み（FR-5.4）

- [ ] `src/maps/googleTypes.ts`: 利用する最小の型（`GoogleMapsNamespace`、`MapsLibrary`、`MarkerLibrary`、`PlacesLibrary`、`PlaceLike` など）
- [ ] `src/maps/loadGoogleMaps.test.ts`: script タグのURL（key・`loading=async`・`language=ja`・`region=JP`・callback）、コールバックで resolve、script の error で reject、`gm_authFailure` で `onAuthFailure` 呼び出し、2回呼んでも script は1つ
- [ ] `src/maps/loadGoogleMaps.ts`
- 確認: `npx vitest run src/maps/loadGoogleMaps.test.ts`

## T5. 店舗検索と変換（FR-1.3, FR-3.2, FR-3.3, NFR-1, NFR-3）

- [ ] `src/places/shop.ts`: `Shop` 型
- [ ] `src/places/searchShops.test.ts`: `boundsAround` の計算、`buildSearchRequest`（fields・maxResultCount 20・language・region・locationRestriction）、`toShop`（全項目あり／任意項目なし／location なしで null／googleMapsURI なしでURLを組み立て／`javascript:` URL を捨てる）、`createShopSearcher` がフェイクの `searchByText` を呼び Shop[] を返す
- [ ] `src/places/searchShops.ts`
- 確認: `npx vitest run src/places/searchShops.test.ts`

## T6. ジャンル単位のキャッシュ（NFR-1, FR-2.8）

- [ ] `src/places/shopCache.test.ts`: 同じジャンルは1回だけ検索、別ジャンルは別に検索、失敗したら次回は再検索
- [ ] `src/places/shopCache.ts`
- 確認: `npx vitest run src/places/shopCache.test.ts`

## T7. ジャンルボタン列（FR-1.1, FR-1.4, NFR-6）

- [ ] `src/ui/genreBar.test.ts`: 定義順にボタンを描画、クリックでコールバック、`setActive` で `aria-pressed` と選択クラスが切り替わる、`<button type="button">` である
- [ ] `src/ui/genreBar.ts`
- 確認: `npx vitest run src/ui/genreBar.test.ts`

## T8. 状態表示（FR-2.5〜2.8, FR-4.2, FR-5.3, FR-5.4）

- [ ] `src/ui/statusView.test.ts`: 読み込み中、件数（「ラーメン: 12件」）、0件、エラー、複数行の問題一覧、`role="status"`
- [ ] `src/ui/statusView.ts`
- 確認: `npx vitest run src/ui/statusView.test.ts`

## T9. 店舗詳細パネル（FR-3.1〜3.5, NFR-3, NFR-6, NFR-7）

- [ ] `src/ui/shopDetail.test.ts`: 店名・住所表示、任意項目ありで表示／なしで非表示、評価の表示形式、Googleマップリンクが `_blank` + `noopener`、HTMLを含む店名が文字列として表示される、閉じるボタンでコールバックと非表示、開いたとき閉じるボタンにフォーカス、「情報提供: Google」表示
- [ ] `src/ui/shopDetail.ts`
- 確認: `npx vitest run src/ui/shopDetail.test.ts`

## T10. ピンレイヤー（FR-2.1, FR-2.2, FR-2.4, FR-3.7）

- [ ] `src/maps/markerLayer.test.ts`（フェイクの Marker・LatLngBounds・Map）: 店舗数ぶんピンを作成、`clear` で全ピンの `map` を null、クリックで `onSelect(shop)`、`highlight` で選択クラス切替、複数件で `fitBounds`・1件で `panTo`、0件では地図を動かさない
- [ ] `src/maps/markerLayer.ts`
- 確認: `npx vitest run src/maps/markerLayer.test.ts`

## T11. 画面の状態管理（FR-1.2, FR-1.3, FR-2.2, FR-2.3, FR-2.5〜2.9, FR-3.1, FR-3.5, FR-3.6）

- [ ] `src/app.test.ts`（フェイクの searcher・layer・view）: `start` で先頭ジャンル選択、切替で前のピンを消し詳細を閉じる、読み込み中→件数表示、0件表示、エラー表示後に別ジャンルを選べる、検索中に別ジャンル押下で古い結果を捨てる、ピン選択で詳細表示と強調、詳細を閉じると強調解除
- [ ] `src/app.ts`
- 確認: `npx vitest run src/app.test.ts`

## T12. 起動処理・画面・スタイル（FR-5.3, FR-5.4, NFR-5, NFR-7）

- [ ] `index.html`（ヘッダー・ジャンルバー・状態表示・地図・詳細パネルの領域）、`src/styles.css`（幅768px未満で詳細を下部シート化、375pxで横スクロールなし、選択中ピンの見た目、地図ロゴを隠さない）
- [ ] `src/main.ts`: 設計の「起動」手順どおりに配線
- 確認: `npm run build`（APIキー未設定でもビルドが通る）

## T13. README（NFR-2, ロールアウト）

- [ ] `README.md`（日本語）: 概要・機能・技術構成・セットアップ・APIキー取得と制限設定（リファラー・API制限・クォータ）・ジャンルの追加方法・コマンド一覧・デプロイ手順・費用の考え方
- 確認: `npm test && npm run lint && npm run build`
