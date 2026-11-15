# 設計 — 動画再生パフォーマンス改善

関連: [requirements.md](./requirements.md) / [investigation.md](./investigation.md)

## 1. 概要

現状のメディア配信は `ブラウザ → Next.js rewrite → Django → boto3 → S3(シドニー)` の4ホップで、
Range 非対応・キャッシュ制御なし・CDN なしのため、スワイプのたびにオリジンから全量を取り直している。

本設計では次の2点を軸に据える。

1. **バイト列をアプリケーションから追い出す** — CloudFront の署名付きURLをAPIレスポンスに同梱し、ブラウザがエッジから直接取得する。Django はメタデータのみを返す。
2. **待ち時間を先に消化する** — 表示中に次コンテンツの先頭を先読みし、スワイプ時点ではバッファ済みの状態にする。

残りの改善（faststart、正規化、一覧API、実行環境）は、この2点の効果を頭打ちにさせないための土台として扱う。

## 2. アーキテクチャ

### 現状

```
ブラウザ --<video src="/api/contents/{id}/media/">--> Next.js(rewrite)
                                                        └─> Django ContentMediaView
                                                              └─> boto3 get_object (全量)
                                                                    └─> S3 ap-southeast-2
```

### 目標

```
       ┌── メタデータ (JSON, 数KB) ─────────────────────────────────┐
ブラウザ ── /api/contents/ ── Next.js(rewrite) ── Django ── SQLite/PG
       │                                    └ media_url を生成(署名のみ、I/Oなし)
       │
       └── メディア本体 ──> CloudFront エッジ(東京) ──(ミス時のみ)──> S3 ap-northeast-1
                            Range対応 / キャッシュ / OAC でバケットは非公開
```

**メディアURLの取得に追加のラウンドトリップを発生させない**ことが要点。一覧APIのレスポンスに `media_url` / `poster_url` を含めるため、
リダイレクト(302)も URL 取得用APIも不要になる。

## 3. 設計判断

| ID | 判断 | 根拠 | 見送った案 |
|---|---|---|---|
| D-1 | メディアURLを **ContentSerializer に同梱**する | 302リダイレクトや別APIだと1RTT(日本→アプリサーバ)増える。一覧取得時点でURLが確定していれば先読みも即座に始められる | `/media/` を302リダイレクトにする案 → 互換用に残すのみ(D-3) |
| D-2 | CloudFront **署名付きURL**、バケットは OAC で非公開 | 要件10.4。バケット全体公開を避けつつエッジ配信を得る | S3 presigned URL の直接利用 → CDN を挟めずオリジン負荷が下がらない |
| D-3 | 既存 `/api/contents/{id}/media/` は**互換用に存続**し、Range・条件付きGET・302を実装 | ブログパーツ等の外部埋め込みや既存リンクを壊さない(要件10.1) | 即時削除 → 影響範囲が読めない |
| D-4 | 署名URLの有効期限を**1時間境界に量子化**する | 毎回異なるURLだとブラウザキャッシュが効かず、要件4.5を満たせない | リクエスト毎のexpiry → URLが毎回変わる |
| D-5 | ランダム抽出を **`random_key` 列 + インデックス**方式へ | `order_by('?')` は全行スキャン。`random_key >= rand()` なら索引探索で O(log n) | 件数から OFFSET 乱択 → フィルタ併用時に毎回 COUNT が必要 |
| D-6 | 動画は **faststart + 720p上限に正規化**し、ABR は見送り | 縦型15秒フィードでは単一ビットレートで十分。HLS導入は変換・保存・プレイヤーの全てにコストがかかる | 全面HLS化 → 要件のスコープ外。効果測定後に再検討 |
| D-7 | 先読みは **`<video>` プール(最大3要素)** | `link rel=preload as=video` はブラウザ対応が不安定。実要素なら `preload="auto"` が確実に効き、遷移時はそのまま表示できる | 単一要素のまま src 差し替え → バッファが毎回破棄される(現状) |
| D-8 | DB は **SQLite WAL 有効化**まで。PostgreSQL 移行は任意タスク | WAL だけで読み取りが書き込みでブロックされなくなる。移行は本スペックの目標達成に必須ではない | 即 PostgreSQL 移行 → 影響が大きく TTFF への寄与は限定的 |
| D-9 | Django 6.0 の `FileResponse` は Range 非対応のため**自前実装** | 実機確認済み(`HTTP_RANGE` の処理を持たない)。`django.views.static.serve` も要件を満たさない | ミドルウェア任せ → 該当機能が存在しない |

## 4. バックエンド設計

### 4.1 メディアURL解決層（新規）

`backend/api/media_url.py`

```python
MODE_CDN   = "cdn"     # CloudFront 署名付きURL
MODE_S3    = "s3"      # S3 presigned URL（CDN未整備時の中間段階）
MODE_PROXY = "proxy"   # 従来のアプリ中継（ローカル開発・フォールバック）

def resolve_media_url(content) -> str | None:
    """Content.path から配信URLを生成する。I/O は行わない（署名は純計算）。"""
```

- `settings.MEDIA_DELIVERY_MODE`（env: `MEDIA_DELIVERY_MODE`、既定 `proxy`）で切替（要件10.2）
- `Content.path` の形式を判別する:
  - `s3://<bucket>/<key>` → バケットが CDN 配下なら署名付きURL、そうでなければ従来経路
  - 相対パス → ローカル `MEDIA_ROOT` 配下として `proxy` 経路
  - `http(s)://` → そのまま返す
- 署名生成は `botocore.signers.CloudFrontSigner`（`cryptography` を requirements に追加）
- **有効期限の量子化**（D-4）:

```python
TTL = 6 * 3600
expires_at = ((int(time.time()) // 3600) + 1) * 3600 + TTL   # 6〜7時間有効、1時間ごとに更新
```

- 署名鍵が未設定、または署名に失敗した場合は **例外を投げず `proxy` 経路のURLを返す**（要件10.3）

### 4.2 ContentSerializer の拡張

```python
class ContentSerializer(...):
    media_url  = serializers.SerializerMethodField()
    poster_url = serializers.SerializerMethodField()
```

- `media_url`: `resolve_media_url(obj)`
- `poster_url`: 動画のみ。`media/thumbs/{content_id}.jpg` を指すURLを生成する。
  **存在確認のための S3 API 呼び出しは行わない**（一覧20件でN+1のI/Oになるため）。`Content.media_version >= 1` を生成済みの印として使う
- 既存の `path` フィールドは互換のため残す

### 4.3 ContentMediaView の再実装

`backend/api/views.py`

```
GET /api/contents/{id}/media/
  ├ mode が cdn/s3 かつ解決成功 → 302 Found (Location: 署名付きURL, Cache-Control: private, max-age=TTL)
  └ それ以外                    → 自前 Range 対応ストリーミング
```

Range 対応の仕様（要件1）:

| 入力 | 応答 |
|---|---|
| `Range` ヘッダなし | `200` / `Accept-Ranges: bytes` / `Content-Length: total` |
| `bytes=start-end`、`bytes=start-`、`bytes=-suffix` | `206` / `Content-Range: bytes s-e/total` / `Content-Length: e-s+1` |
| 範囲外 | `416` / `Content-Range: bytes */total` |
| 書式不正 | 無視して `200`（RFC 9110 準拠） |

- S3 経路は `s3.get_object(Bucket=..., Key=..., Range="bytes=s-e")` にそのまま委譲する（アプリ側で読み飛ばさない）
- ローカル経路は `file.seek(start)` + 残量を数えるジェネレータ
- チャンクサイズを **8KB から 256KB へ**（investigation B-7）
- 共通ヘッダ: `Accept-Ranges: bytes` / `Cache-Control: public, max-age=2592000, immutable` / `ETag`（S3のETag、ローカルは mtime+size）/ `Last-Modified`
- `If-None-Match` / `If-Modified-Since` に対し `304` を返す（要件4.3）。`ConditionalGetMiddleware` は Range と併用すると誤作動するため、**ビュー内で明示的に判定する**
- 共通部分は `backend/api/ranged_response.py` に切り出す

### 4.4 ランダム抽出の置き換え（要件7）

`Content.random_key`（FloatField, db_index=True）を追加する。

```python
if params.get('random') == 'true':
    pivot = random.random()
    qs = qs.filter(random_key__gte=pivot).order_by('random_key')
    # 件数が足りない場合は先頭から補完（ラップアラウンド）
```

- `save()` 時に未設定なら採番し、データ移行で既存行を一括採番する
- ページングは `random_key` のカーソル方式にして `page=N` の OFFSET を避ける
  - レスポンスに `next_cursor` を含め、フロントは次ページ取得時にそれを渡す
  - 互換のため `page` パラメータも当面受け付ける
- 併せて、使われていない `_weighted_random_response`（1ページあたり20回の `order_by('?')` を発行する）を削除する

### 4.5 インデックス（要件7.3）

`0012_content_performance_indexes.py`:

| 対象 | 種別 |
|---|---|
| `random_key` | 単一 |
| `(type, random_key)` | 複合 |
| `(user, created_at)` | 複合 |
| `created_at` | 単一（既定 `ordering` 用） |
| `media_version` | 単一（正規化バッチの絞り込み用） |

### 4.6 設定の外部化（要件3.4 / 3.5 / 8.2 / 8.3）

`settings.py` からハードコードを除去し、`python-dotenv` で `.env` を読み込む。

| 環境変数 | 既定 | 用途 |
|---|---|---|
| `DJANGO_DEBUG` | `False` | デバッグ |
| `DJANGO_SECRET_KEY` | (必須) | シークレット |
| `MEDIA_DELIVERY_MODE` | `proxy` | 配信方式（D-1 / D-3） |
| `AWS_REGION` | `ap-northeast-1` | リージョン |
| `MEDIA_S3_BUCKET` | — | 配信元バケット |
| `CLOUDFRONT_DOMAIN` | — | 配信ドメイン |
| `CLOUDFRONT_KEY_PAIR_ID` / `CLOUDFRONT_PRIVATE_KEY_PATH` | — | 署名鍵 |
| `MEDIA_SIGNED_URL_TTL` | `21600` | 署名URL有効期間(秒) |
| `MEDIA_CACHE_MAX_AGE` | `2592000` | キャッシュ有効期間(秒) |

`.env.example` を追加し、`.env` を `.gitignore` に加える。
**現在コミット済みの AWS キーは無効化・ローテーション済みであることが前提**（investigation.md 第4節）。

### 4.7 SQLite WAL（要件8.6 / D-8）

`connection_created` シグナルで以下を適用する。

```
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
```

## 5. インフラ設計

### 5.1 CloudFront

| 項目 | 設定 |
|---|---|
| オリジン | S3 `ap-northeast-1` バケット、**OAC** 経由（バケットは非公開のまま） |
| 許可メソッド | `GET, HEAD` のみ |
| Origin Shield | 有効（オリジン負荷とリージョン間転送を削減） |
| キャッシュポリシー | TTL 30日。CloudFront は署名パラメータ（`Expires`/`Signature`/`Key-Pair-Id`）をキャッシュキーから除外するため、D-4 の量子化がなくてもエッジは共有される（量子化はブラウザキャッシュのために必要） |
| 圧縮 | 動画は無効（既に圧縮済み） |
| ビューワアクセス | 署名付きURL必須 |
| ログ | 標準ログを有効化し `x-edge-result-type` でヒット率を集計（要件2.5 / 9.3） |

### 5.2 リージョン移行（要件3）

段階移行とし、**一斉カットオーバーは行わない**。

1. 東京バケットを作成する
2. `sync_media_region` コマンドで `ap-southeast-2` から `ap-northeast-1` へコピーする（`copy_object` によるサーバ間コピー。ローカルを経由しない）
3. コピーが完了した `Content.path` のみを1件ずつ新バケットへ書き換える（途中で中断しても整合が保たれる）
4. 解決層は**両バケットを同時に扱える**ため、移行途中でも全コンテンツが再生可能（要件3.2）
5. 全件移行後に旧バケットを削除する

## 6. 動画正規化設計（要件5）

### 6.1 新規コマンド `normalize_video`

`backend/tools/management/commands/normalize_video.py`

```
対象: Content.type == video かつ media_version < CURRENT_MEDIA_VERSION
処理:
  1. ffprobe で moov 位置・解像度・ビットレート・コーデックを取得
  2. 判定
     ├ h264/aac かつ 高さ <= 720 かつ ビットレート <= 上限
     │    → 再エンコードせず remux のみ:
     │      -c copy -movflags +faststart              (要件5.5 画質を劣化させない)
     └ それ以外
          → -c:v libx264 -crf 23 -preset veryfast -vf scale=-2:720
            -c:a aac -b:a 128k -movflags +faststart
  3. サムネイル生成: 中間フレーム1枚を media/thumbs/{content_id}.jpg へ
  4. S3 へアップロード（move_content_to_s3 のアップロード処理を共通化して再利用）
  5. Content.media_version = CURRENT_MEDIA_VERSION を保存   (要件5.6 冪等性)
```

- `--dry-run` で判定結果のみを出力する
- 中断時は `media_version` が更新されないため、再実行で続きから処理される

### 6.2 `split_video_as_short` の修正（investigation B-14）

`-f segment` と `-movflags +faststart` は併用できない（セグメントマルチプレクサは faststart を適用しない）。
分割後に各チャンクへ remux パスを追加する。

```python
subprocess.run(["ffmpeg", "-i", chunk, "-c", "copy", "-movflags", "+faststart", out, "-y"])
```

### 6.3 `moov` 位置の判定

MP4 の先頭から atom を順に読み、`mdat` より前に `moov` が現れるかを確認する軽量チェックを
`backend/tools/mp4_utils.py` に実装する（ffprobe を起動せずに済むため一括判定が速い）。

## 7. フロントエンド設計

### 7.1 メディアURL解決の一本化

`frontend/src/lib/api.ts`

```ts
export const getMediaUrl = (content: Content) =>
  content.media_url ?? (content.path ? `${BASE_URL}/contents/${content.id}/media/` : content.link);

export const getPosterUrl = (content: Content) => content.poster_url ?? undefined;
```

`Content` 型に `media_url?: string` / `poster_url?: string` を追加する。
[FeedPlayer.tsx:530](../../../frontend/src/components/FeedPlayer.tsx#L530) の独自URL組み立ては `getMediaUrl()` に置き換える
（要件8.5 — CDN配信時に Next.js プロキシを通らなくなる）。

### 7.2 次コンテンツ解決の純粋関数化（要件6.2）

現在 [goTo()](../../../frontend/src/components/FeedPlayer.tsx#L247-L360) には「シリーズスキップ」「広告挿入」「追加ページ取得」が混在しており、
先読み側から「次に本当に表示されるもの」を知る手段がない。副作用のない解決関数を切り出す。

`frontend/src/components/feed/resolveNext.ts`

```ts
export function resolveNextIndex(
  contents: Content[], from: number, direction: 1 | -1,
  adMap: Map<number, AdContent>,
): { kind: "content"; index: number } | { kind: "ad"; index: number } | { kind: "exhausted" }
```

`goTo()` はこの関数の結果に従って状態遷移のみを行う形に整理する。
先読み側は同じ関数を呼び、`kind === "content"` のときだけ対象を先読みする。

### 7.3 `<video>` プール（要件6.1 / 6.3 / 6.7 / D-7）

`frontend/src/components/feed/VideoPool.tsx`

- 保持する要素は **最大3つ**（前 / 現在 / 次）。`content.id` をキーにする
- 現在の要素: `preload="auto"` / 可視 / 再生
- 次の要素: `preload="auto"` / `muted` / 非表示(`visibility:hidden`) / **再生はしない**
- 前の要素: `preload="metadata"` に降格（戻る操作の高速化）
- プールから外れた要素は `src=""` にして `load()` を呼び、明示的に解放する
- 遷移時は要素を作り直さず **表示を切り替えるだけ** にする → 先読みバッファが維持される（要件6.3）

### 7.4 poster と低速回線対応

- `<video poster={getPosterUrl(current)}>` を設定する（要件6.5）
- `navigator.connection` の `saveData` / `effectiveType` を参照し、`saveData === true` または `effectiveType` が `2g` / `slow-2g` の場合は**先読み件数を1件から0件に縮退**させる（要件6.6）
- 先読みの失敗は `onError` で握りつぶし、UI には出さない（要件6.8）

### 7.5 初期表示の直列解消（要件7.5 / investigation B-16）

- [feed/page.tsx](../../../frontend/src/app/feed/page.tsx) をサーバコンポーネントで初回1ページ分を取得し、`initialContents` として渡す
- [FeedPlayer.tsx:146-148](../../../frontend/src/components/FeedPlayer.tsx#L146-L148) のレンダー本体での `fetchInitialContents()` 呼び出しを `useEffect` へ移す（要件7.6）
- SSR された HTML に先頭コンテンツの `poster_url` への `<link rel="preload" as="image">` を含め、初回フレーム表示を前倒しする

## 8. 計測設計（要件9）

### 8.1 クライアント計測

`frontend/src/lib/playbackMetrics.ts`

| 指標 | 取得方法 |
|---|---|
| TTFF | 遷移確定時刻（`goTo` 完了）から `loadeddata` または `playing` の早い方まで |
| リバッファ | `waiting` から `playing` までの間隔を累積し、`ended` または切替時に確定 |
| 先読みヒット | 遷移時点で `video.readyState >= HAVE_FUTURE_DATA` だったか |
| キャッシュ | `PerformanceResourceTiming.transferSize === 0`（ブラウザキャッシュ）、および `x-cache` ヘッダ |

- **サンプリング率 10%**（`MEDIA_METRICS_SAMPLE_RATE`）。計測自体が体感を悪化させないため
- `navigator.sendBeacon` で `POST /api/metrics/playback/` へ送信する（再生を妨げない）

### 8.2 保存と参照

- 新モデル `PlaybackMetric`（content_id, ttff_ms, rebuffer_ms, rebuffer_count, preload_hit, cache_hit, delivery_mode, created_at）
- `delivery_mode` を記録することで **proxy と cdn を同一条件で比較できる**（要件9.4）
- 集計コマンド `report_playback_metrics`（配信方式別に p50 / p95 / リバッファ率を出力）
- CloudFront の `x-edge-result-type` 集計でヒット率を確認する（要件2.5）

## 9. エラーハンドリングとフォールバック

| 障害 | 挙動 |
|---|---|
| 署名鍵が未設定 / 署名失敗 | `proxy` URL を返す。ログのみ（要件10.3） |
| CDN が 403 / 5xx を返す | `<video onError>` で `proxy` URL に差し替えて1回だけ再試行 |
| S3 オブジェクト不在 | `404`。プレイヤーは次のコンテンツへ自動的に進む |
| Range 書式不正 | `416` または `200`（RFC 9110） |
| 先読み失敗 | 無視し、現在の再生に影響させない（要件6.8） |
| メトリクス送信失敗 | 無視 |

## 10. テスト戦略

| 層 | 内容 |
|---|---|
| 単体(backend) | Range パーサ（正常 / 末尾指定 / 範囲外 / 不正）、`resolve_media_url` の各モードとフォールバック、署名URLが同一時間内で不変であること、`random_key` 抽出の件数と重複 |
| 単体(frontend) | `resolveNextIndex` の網羅（シリーズ連続、広告挿入位置、末尾、後退方向） |
| 結合 | `/media/` が `206` / `Content-Range` / `304` を正しく返すこと、`cdn` モードで `302` を返すこと |
| 冪等性 | `normalize_video` の二重実行で再変換が走らないこと |
| 性能 | 一覧API p95、TTFF p50 / p95 を**施策適用前にベースラインとして取得**しておく（要件9.4） |
| 回帰 | ブログパーツ・記事サムネイル・検索画面・プロフィール画面のメディア表示が壊れていないこと |

## 11. 要件トレーサビリティ

| 要件 | 対応する設計 |
|---|---|
| 1 Range | 4.3 |
| 2 CDN | 4.1, 4.2, 5.1 |
| 3 リージョン | 4.6, 5.2 |
| 4 キャッシュ | 4.3, D-4 |
| 5 ファイル最適化 | 6.1, 6.2, 6.3 |
| 6 先読み | 7.2, 7.3, 7.4 |
| 7 一覧API | 4.4, 4.5, 7.5 |
| 8 実行環境 | 4.6, 4.7, 7.1 |
| 9 計測 | 8.1, 8.2 |
| 10 移行・アクセス制御 | 4.1, 4.3, 5.1, 5.2, 9 |
