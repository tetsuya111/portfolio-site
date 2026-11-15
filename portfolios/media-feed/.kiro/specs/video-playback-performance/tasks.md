# 実装タスク — 動画再生パフォーマンス改善

関連: [requirements.md](./requirements.md) / [design.md](./design.md) / [investigation.md](./investigation.md)

実施順は「計測 → 低リスクな即効策 → 配信経路の刷新 → 資産の最適化 → 仕上げ」とする。
フェーズ1を終えた時点で一度計測し、フェーズ2以降の投資判断に使う。

---

## フェーズ0: 前提作業と計測基盤

- [ ] 0. **漏洩済み AWS アクセスキーの無効化とローテーション**
  - IAM で `（キーIDは公開用に伏せ字）` を無効化し、新しいキーを発行する
  - 新キーは `.env` にのみ置き、Git 管理対象に含めない
  - メディア配信用には S3 読み取りのみの最小権限ロールを用意する
  - _これ以降の全タスクの前提。[settings.py:155-156](../../../backend/config/settings.py#L155-L156) は Git にコミット済み_
  - _要件: 3.5_

- [x] 1. 設定の外部化
  - [x] 1.1 `python-dotenv` を `requirements.txt` に追加し、`settings.py` 先頭で `.env` を読み込む
  - [x] 1.2 `DJANGO_DEBUG` / `DJANGO_SECRET_KEY` / `AWS_*` / `MEDIA_*` / `CLOUDFRONT_*` を環境変数化し、ハードコードを削除する（`DEBUG` の既定は本番安全な `False`。開発機は `.env` の `DJANGO_DEBUG=True` で従来どおり）
  - [x] 1.3 `.env.example` を追加し、`.gitignore` に `.env` を追加する
  - [x] 1.4 `CLOUDFLARE_TURNSTILE_SECRET_KEY` も同様に環境変数へ移す
  - _要件: 3.4, 3.5, 8.2, 8.3_

- [ ] 2. 再生メトリクスの収集基盤
  - [ ] 2.1 `PlaybackMetric` モデルと migration `0012` を追加する（content_id, ttff_ms, rebuffer_ms, rebuffer_count, preload_hit, cache_hit, delivery_mode, created_at）
  - [ ] 2.2 `POST /api/metrics/playback/` を追加する（未認証可、レート制限あり、バリデーション失敗時は静かに破棄）
  - [ ] 2.3 `frontend/src/lib/playbackMetrics.ts` を実装する（TTFF、リバッファ、先読みヒット、キャッシュ判定、サンプリング率10%、`sendBeacon` 送信）
  - [ ] 2.4 `FeedPlayer` の `<video>` に計測フックを接続する
  - [ ] 2.5 集計コマンド `report_playback_metrics` を実装する（配信方式別に p50 / p95 / リバッファ率）
  - _要件: 9.1, 9.2, 9.3, 9.4_

- [ ] 3. **ベースライン計測を実施し記録する**
  - フェーズ1以降の変更を入れる前に、TTFF p50 / p95、一覧API p95、リバッファ率を取得する
  - 結果を `.kiro/specs/video-playback-performance/baseline.md` に残す
  - _以降の全フェーズの効果測定はこの値との比較で行う_
  - _要件: 9.4_

---

## フェーズ1: 低リスクな即効策（インフラ変更を伴わない）

- [x] 4. Range 対応レスポンスの実装
  - [x] 4.1 `backend/api/ranged_response.py` に Range ヘッダのパーサを実装する（`bytes=s-e` / `bytes=s-` / `bytes=-suffix` / 不正 / 範囲外）
  - [x] 4.2 パーサの単体テストを書く（境界値、`416` を返す条件、不正時に `200` へフォールバックすること）
  - [x] 4.3 ローカルファイル用の Range レスポンス生成（`seek` + 残量カウントのジェネレータ、チャンク 256KB）を実装する
  - [x] 4.4 S3 用の Range レスポンス生成（`get_object(Range=...)` に委譲。サイズ確認の往復を省くため判定ごとS3に委ねる）を実装する
  - [x] 4.5 `ContentMediaView` を 4.3 / 4.4 を使う形に書き換える。`Accept-Ranges: bytes` を常に付与する
  - [x] 4.6 `206` / `416` / `200` を検証する結合テストを書く
  - _要件: 1.1, 1.2, 1.3, 1.4, 1.6_

- [x] 5. キャッシュ制御ヘッダの付与
  - [x] 5.1 `Cache-Control: public, max-age=<MEDIA_CACHE_MAX_AGE>, immutable` を付与する
  - [x] 5.2 `ETag`（S3のETag / ローカルは mtime+size）と `Last-Modified` を設定する
  - [x] 5.3 `If-None-Match` / `If-Modified-Since` をビュー内で判定し `304` を返す（Range との併用を壊さないこと）
  - [x] 5.4 `304` を返すことのテストを書く（ブラウザ側の再要求有無は実機計測に回す）
  - _要件: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 6. プレイヤーの先読み対応
  - [x] 6.1 `frontend/src/components/feed/resolveNext.ts` に `resolveNextIndex()` を純粋関数として切り出す
  - [ ] 6.2 `resolveNextIndex` の単体テストを書く（**フロントにテストランナーが無い**。vitest 等の導入判断が必要）
  - [ ] 6.3 `goTo()` を `resolveNextIndex()` の結果に従う形へ整理する（現状は先読み側のみが利用。goTo 本体の整理は未着手）
  - [x] 6.4 `frontend/src/components/feed/VideoPool.tsx` を実装する（最大3要素、前/現在/次、`preload` の出し分け、退役要素の `removeAttribute("src")` + `load()` 解放）
  - [x] 6.5 `FeedPlayer` の単一 `<video>` を `VideoPool` に置き換える。遷移時に要素を作り直さないこと
  - [x] 6.6 `navigator.connection` の `saveData` / `effectiveType` による先読み縮退を実装する
  - [x] 6.7 先読み失敗時に UI へエラーを出さないことを確認する
  - _要件: 6.1, 6.2, 6.3, 6.4, 6.6, 6.7, 6.8_

- [x] 7. SQLite WAL の有効化
  - `backend/api/apps.py` の `ApiConfig.ready()` で `connection_created` に接続し、`journal_mode=WAL` / `synchronous=NORMAL` / `busy_timeout=5000` を適用する
  - _要件: 8.6_

- [ ] 8. **フェーズ1の効果測定** — タスク3のベースラインと比較し、記録する
  - _要件: 9.4_

---

## フェーズ2: 配信経路の刷新（CDN）

- [x] 9. メディアURL解決層
  - [x] 9.1 `backend/api/media_url.py` に `resolve_media_url()` と `MEDIA_DELIVERY_MODE` の切替を実装する（既定は `proxy` なので挙動は変わらない）
  - [x] 9.2 CloudFront 署名を実装する（`CloudFrontSigner`、`cryptography` を requirements に追加）
  - [x] 9.3 有効期限の1時間境界への量子化を実装する（S3 presigned は窓ごとに `lru_cache` でURLを固定）
  - [x] 9.4 署名失敗・鍵未設定時に `proxy` へフォールバックする処理を実装する
  - [x] 9.5 単体テストを書く（各モード、`s3://` / 相対パス / `http(s)://` の判別、同一時間内で署名URLが不変であること、フォールバック）
  - _要件: 2.1, 2.4, 10.2, 10.3, 10.4, 10.5_

- [ ] 10. CloudFront ディストリビューションの構築
  - [ ] 10.1 OAC でS3オリジンに接続し、バケットは非公開のままにする
  - [ ] 10.2 `GET, HEAD` のみ許可、TTL 30日、Origin Shield を有効化する
  - [ ] 10.3 署名付きURL必須（トラステッドキーグループ）を設定し、署名鍵を発行する
  - [ ] 10.4 標準ログを有効化し、`x-edge-result-type` によるヒット率の集計手順を用意する
  - _要件: 2.1, 2.2, 2.3, 2.5, 10.4_

- [x] 11. APIレスポンスへのURL同梱
  - [x] 11.1 `ContentSerializer` に `media_url` / `poster_url` を追加する（S3へのI/Oを発生させないこと）
  - [ ] 11.2 `ContentMediaView` に、cdn / s3 モードでの `302` リダイレクトを追加する（互換経路として存続）
  - [x] 11.3 一覧20件のレスポンスで追加のI/Oが発生しないことをテストで検証する
  - _要件: 2.4, 10.1, 10.2_

- [ ] 12. フロントエンドのURL解決一本化
  - [x] 12.1 `Content` 型に `media_url` / `poster_url` を追加する（タスク6で先行実施）
  - [x] 12.2 `getMediaUrl()` を `media_url` 優先に変更し、`getPosterUrl()` を追加する（タスク6で先行実施）
  - [x] 12.3 FeedPlayer の独自URL組み立てを `getMediaUrl()` に置き換え、コメントアウトされた旧実装を削除する
  - [ ] 12.4 CDN が 403 / 5xx を返した場合に `proxy` URL で1回だけ再試行する処理を入れる
  - [ ] 12.5 記事・検索・プロフィール・ブログパーツの各画面で表示が壊れていないことを確認する
  - _要件: 2.4, 8.5, 10.1, 10.3_

- [ ] 13. **フェーズ2の効果測定** — TTFF とCDNヒット率を記録する。ヒット率90%未満ならキャッシュポリシーを見直す
  - _要件: 2.2, 2.5, 9.4_

---

## フェーズ3: リージョン移行

- [ ] 14. 東京リージョンへの移行
  - [x] 14.0 バケットごとにリージョンを解決する `api/s3_client.py` を追加し、`views.py` / `move_content_to_s3.py` を共通化する
  - [x] 14.1 既定リージョンを `ap-northeast-1` にし、旧バケットのリージョンを `MEDIA_BUCKET_REGIONS` で上書きできるようにする（新旧併存のため）
  - [x] 14.2 `ap-northeast-1` にバケットを用意する → `junk-porn-feed-site-747034604623-ap-northeast-1-an`
  - [x] 14.3 `sync_media_region` コマンドを実装する（`copy_object` によるサーバ間コピー、1件ずつ `Content.path` を更新、中断・再開が可能）
  - [x] 14.4 **S3オブジェクトのコピーを完了する** — `aws s3 sync` で890オブジェクト / 1,762,454,287バイトを移送。両バケットの件数・サイズ一致、差分ゼロを確認済み
  - [x] 14.5 `.env` の `MEDIA_S3_BUCKET` を東京バケットへ切り替える（新規アップロード先が東京になる）
  - [ ] 14.6 **本番DBに対して `sync_media_region` を実行し `Content.path` を差し替える**（このマシンに `db.sqlite3` が無いため未実施。実行するまで既存コンテンツの配信はシドニーのまま）
    - `python manage.py sync_media_region --dest-bucket junk-porn-feed-site-747034604623-ap-northeast-1-an --dry-run` で対象を確認してから実行する
    - コピーは済んでいるので `head_object` で検出され、path の更新のみが走る
  - [ ] 14.7 解決層が新旧両バケットを同時に扱えることをテストで確認する
  - [ ] 14.8 全件移行を確認後、`MEDIA_BUCKET_REGIONS` を空にし、旧バケット `junk-porn-feed-site` を削除する（**DBのpath差し替え完了までは削除しないこと**）
  - [ ] 14.9 CloudFront のオリジンを新バケットに向ける
  - _要件: 3.1, 3.2, 3.3, 3.4_

---

## フェーズ4: 動画ファイルの最適化

- [ ] 15. faststart 判定と分割処理の修正
  - [ ] 15.1 `backend/tools/mp4_utils.py` に moov 位置の判定を実装する（atom を先頭から走査）
  - [ ] 15.2 判定の単体テストを書く（faststart 済み / 未済の両方）
  - [ ] 15.3 [split_video_as_short.py](../../../backend/tools/management/commands/split_video_as_short.py) の分割後に remux パスを追加し、各チャンクを faststart 化する
  - _要件: 5.1, 5.2_

- [ ] 16. 正規化コマンド
  - [ ] 16.1 `Content.media_version` フィールドと migration を追加する
  - [ ] 16.2 `normalize_video` コマンドを実装する（remux のみ / 再エンコードの判定、720p上限、faststart、`--dry-run`）
  - [ ] 16.3 サムネイル生成と `media/thumbs/{id}.jpg` へのアップロードを実装する
  - [ ] 16.4 S3 アップロード処理を `move_content_to_s3` と共通化する
  - [ ] 16.5 冪等性のテストを書く（二重実行で再変換されないこと、中断後の再開）
  - [ ] 16.6 既存動画に対して一括実行する
  - _要件: 5.3, 5.4, 5.5, 5.6_

- [ ] 17. poster の適用
  - `<video poster>` に `getPosterUrl()` を接続し、初回フレーム描画までの黒画面を解消する
  - _要件: 6.5_

- [x] 18. `move_content_to_s3` の不具合修正
  - [x] 18.1 `if not (id or secret)` を `and` に修正する
  - [x] 18.2 `TransferConfig` の `multipart_threshold` / `multipart_chunksize` が `1024 * 25`（25KB）になっていた。コメント通り 25MB に修正する（25KBだと10MBの動画が400パートに分割されアップロードが極端に遅くなる）
  - _investigation 第4節_

---

## フェーズ5: 一覧APIと実行環境

- [ ] 19. ランダム抽出の置き換え
  - [ ] 19.1 `Content.random_key` フィールドと、既存行を一括採番するデータ移行を追加する
  - [ ] 19.2 `save()` で未設定時に採番する処理を追加する
  - [ ] 19.3 `ContentListView` の `order_by('?')` を `random_key` 方式に置き換える（件数不足時のラップアラウンドを含む）
  - [ ] 19.4 `next_cursor` によるページングを実装し、`page` パラメータの互換を維持する
  - [ ] 19.5 未使用の `_weighted_random_response` を削除する
  - [ ] 19.6 単体テストを書く（件数、重複なし、フィルタ併用、ラップアラウンド）
  - _要件: 7.1, 7.2_

- [ ] 20. インデックス追加
  - `random_key` / `(type, random_key)` / `(user, created_at)` / `created_at` / `media_version` を追加し、適用前後のクエリ時間を比較する
  - _要件: 7.2, 7.3_

- [ ] 21. N+1 クエリの解消
  - 一覧取得時のクエリ数を計測し、タグ・シリーズ詳細の取得で N+1 が発生していないことを確認する（`select_related('detail__series')` の追加を含む）
  - _要件: 7.4_

- [ ] 22. 初期表示の直列解消
  - [ ] 22.1 [feed/page.tsx](../../../frontend/src/app/feed/page.tsx) をサーバコンポーネントで初回1ページ分を取得する形にする
  - [ ] 22.2 [FeedPlayer.tsx:146-148](../../../frontend/src/components/FeedPlayer.tsx#L146-L148) のレンダー本体での副作用を `useEffect` へ移す
  - [ ] 22.3 先頭コンテンツの poster への `<link rel="preload" as="image">` を SSR 出力に含める
  - _要件: 7.5, 7.6_

- [ ] 23. 本番実行環境
  - [ ] 23.1 開発用サーバから本番用アプリケーションサーバへ移行する（Linux: gunicorn、Windows 開発機: waitress）
  - [ ] 23.2 `start.sh` と readme を更新し、開発用と本番用の起動手順を分ける
  - [ ] 23.3 本番で `DEBUG=False` で動作することを確認する
  - [ ] 23.4 同時視聴時のメモリ使用量が動画サイズに比例しないことを負荷試験で確認する
  - _要件: 8.1, 8.2, 8.4_

---

## フェーズ6: 仕上げ

- [ ] 24. 最終計測と目標達成の確認
  - TTFF p50 500ms以下 / p95 1.5秒以下、一覧API p95 150ms以下、リバッファ率1%未満、CDNヒット率90%以上を確認する
  - 未達の指標があれば原因を記録し、追加タスクを起票する
  - _要件: 成功指標、9.4, 9.5_

- [ ] 25. 旧経路の整理
  - [ ] 25.1 `ContentMediaView` のストリーミング経路に、フォールバック専用であることを明記する
  - [ ] 25.2 使われなくなったコメントアウト済みコードを削除する
  - [ ] 25.3 readme に配信アーキテクチャと `MEDIA_DELIVERY_MODE` の説明を追記する
  - _要件: 10.6_

---

## 任意（効果測定後に判断）

- [ ] 26. PostgreSQL への移行（SQLite WAL で不足と判明した場合のみ）— _要件: 8.6_
- [ ] 27. HLS / ABR の導入（単一ビットレートで目標未達の場合のみ）— _requirements スコープ外に記載_
