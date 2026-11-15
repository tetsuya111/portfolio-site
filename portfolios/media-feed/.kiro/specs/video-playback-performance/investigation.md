# 現状調査レポート — 動画再生の速度低下要因

対象コミット: `7def9b6` / 調査日: 2026-09-20

## 1. 現在の配信経路

```
ブラウザ <video src="/api/contents/{id}/media/">
   ↓ (1) Next.js rewrites プロキシ (Node)            next.config.ts:29-38
   ↓ (2) Django ContentMediaView (WSGI)              backend/api/views.py:385-411
   ↓ (3) boto3 s3.get_object (オブジェクト全体)      backend/api/views.py:402
   ↓ (4) S3 バケット junk-porn-feed-site / ap-southeast-2 (シドニー)
```

動画のバイト列が **4ホップ**（うち2つはアプリケーションサーバのメモリを経由）を通過する。
CDN は介在せず、署名付きURLによる直接配信も行っていない。

## 2. 特定したボトルネック

| # | 箇所 | 内容 | 影響度 |
|---|---|---|---|
| B-1 | [views.py:397-411](../../../backend/api/views.py#L397-L411) | **HTTP Range 未対応**。`Range` ヘッダを無視し常にオブジェクト全体を返す。`Accept-Ranges` も `206` も返さない | 致命的 |
| B-2 | [views.py:402](../../../backend/api/views.py#L402) | S3 のバイト列を Django プロセスが**全量中継**。同時視聴者数に比例してアプリのメモリ／スレッドを消費 | 致命的 |
| B-3 | [settings.py:157](../../../backend/config/settings.py#L157) | S3 リージョンが **`ap-southeast-2`（シドニー）**。日本からの RTT は約 110〜130ms、東京(`ap-northeast-1`)比で 5〜8 倍 | 大 |
| B-4 | 全体 | **CDN(CloudFront)なし**。同一動画へのリクエストが毎回オリジン(S3)まで到達する | 大 |
| B-5 | [views.py:403-409](../../../backend/api/views.py#L403-L409) | レスポンスに `Cache-Control` / `ETag` / `Last-Modified` が無い。ブラウザキャッシュも条件付きGETも効かない。再視聴・巻き戻しのたびに再ダウンロード | 大 |
| B-6 | [next.config.ts:29-38](../../../frontend/next.config.ts#L29-L38) | `BASE_URL = "/api"`([api.ts:6](../../../frontend/src/lib/api.ts#L6)) のため、**動画ストリームが Next.js の rewrite プロキシを経由**する。Node の単一プロセスが大容量ストリームで飽和する | 大 |
| B-7 | [views.py:404](../../../backend/api/views.py#L404) | `iter_chunks(chunk_size=8192)` = **8KB 刻み**。1本の動画で数万回の write が発生し、syscall／WSGI のオーバーヘッドが支配的になる | 中 |
| B-8 | [FeedPlayer.tsx:681-690](../../../frontend/src/components/FeedPlayer.tsx#L681-L690) | `<video>` に **`preload` も `poster` も無い**。次コンテンツの先読みも無く、スワイプ後にゼロから接続が始まる | 大 |
| B-9 | [FeedPlayer.tsx:530](../../../frontend/src/components/FeedPlayer.tsx#L530) | `<video>` は**常に1要素のみ**。`goTo()` で `src` が差し替わるため、既存のバッファは都度破棄される | 大 |
| B-10 | [views.py:113-114](../../../backend/api/views.py#L113-L114) | 一覧APIの `random=true` が `order_by('?')`。SQLite では**全行スキャン＋ソート**。動画表示前段の待ち時間に直結 | 中 |
| B-11 | [models.py:46-60](../../../backend/api/models.py#L46-L60) | `Content` に `type` / `user` / `created_at` の**インデックスが無い**。`ordering = ['-created_at']` と併用され毎回ソートが走る | 中 |
| B-12 | [settings.py:12,62-66](../../../backend/config/settings.py#L12) | **`DEBUG = True`** かつ **SQLite**。`DEBUG=True` は全SQLをメモリ保持し続け、SQLite は書き込みロックで一覧APIを詰まらせる | 中 |
| B-13 | [start.sh:9](../../../start.sh#L9) | 本番想定でも **`manage.py runserver`**（開発用サーバ）。ストリーミング用途の並行処理性能が無い | 中 |
| B-14 | [split_video_as_short.py:99-108](../../../backend/tools/management/commands/split_video_as_short.py#L99-L108) | ffmpeg 分割が `-c copy` のみで **`-movflags +faststart` が無い**。moov atom が末尾にある動画は、全体をダウンロードするまで再生が始まらない | 大 |
| B-15 | 収集バッチ全般 | 取得した動画を**無変換で保存**。解像度・ビットレートが不揃いで、縦型フィードに対し過剰な品質のファイルが混在する。ABR(HLS/DASH)も無い | 中 |
| B-16 | [FeedPlayer.tsx:146-148](../../../frontend/src/components/FeedPlayer.tsx#L146-L148) | `if (contents.length == 0) { fetchInitialContents(); }` が**レンダー本体で副作用を実行**している。初期表示で余分なフェッチが走りうる。加えて [feed/page.tsx](../../../frontend/src/app/feed/page.tsx) は `initialContents={[]}` を渡すため、**初回コンテンツが SSR されず**、一覧取得 → 動画取得が直列になる | 中 |

## 3. 想定される時間内訳（日本国内・モバイル回線からの初回再生、推定）

| 区間 | 現状(推定) | 改善後の目標 |
|---|---|---|
| 一覧API応答 (`order_by('?')` 含む) | 300〜900ms | < 150ms |
| メディアURL解決〜S3接続 (Next→Django→Sydney) | 250〜500ms | < 50ms (CDNエッジ) |
| 先頭セグメント到達 (moov atom 位置に依存) | 500ms〜動画全長分 | < 300ms |
| **合計 TTFF** | **1.5〜10秒以上** | **< 1.0秒 (p95)** |

## 4. 付随して確認された問題（本スペックの主対象外だが要対応）

- [settings.py:155-156](../../../backend/config/settings.py#L155-L156) に **AWS アクセスキーがハードコードされ Git にコミット済み**。署名付きURL方式へ移行する際は必ずキーをローテーションすること。
- [move_content_to_s3.py:31](../../../backend/tools/management/commands/move_content_to_s3.py#L31) の `if not (id or secret)` は `and` の誤りと思われる。
- Web からの動画アップロード機能は未実装（S3 への配置は `move_content_to_s3` バッチのみ）。
