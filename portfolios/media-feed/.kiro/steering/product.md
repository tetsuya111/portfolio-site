---
inclusion: always
---

# プロダクト概要

- **名称**: アダルトフィードサイト（リポジトリ名: `adult_feed_site`、アプリ内の表記は `website`）
- **概要**: 複数のアダルト動画・画像サイトからバッチでコンテンツを収集し、短尺フィード形式（縦スワイプ）で閲覧できるWebアプリケーション。収集したコンテンツをまとめた「記事」を作成でき、記事一覧は埋め込み用HTML（ブログパーツ）として外部ブログに貼り付けられる。
- **狙い**: 収集したコンテンツを入り口として、フィード・記事・ブログパーツから元サイト（アフィリエイトリンク）へ送客する。クリックは `ClickCount` で計測する。
- **現状**: ローカル開発段階。`DEBUG = True`、SQLite、`CORS_ALLOW_ALL_ORIGINS = True` のまま。本番公開に向けた設定（秘密情報の環境変数化、ホスト制限、年齢確認）は未整備で、詳細は [.kiro/steering/tech.md](./tech.md) の「本番公開前の未対応事項」を参照。既知の課題としてフィードの動画再生が遅く、改善の要件を [.kiro/specs/video-playback-performance/](../specs/video-playback-performance/requirements.md) にまとめている。

## 想定ユーザー

- **閲覧者**: 未ログインでも閲覧できる。登録するとブックマーク・フォロー・コメント・記事作成が使える。
- **アフィリエイター**: ブログパーツを生成して自分のブログに貼り、送客数を `/click-stats` で確認する（`UserDetail.is_affiliate`）。
- **投稿者・記事作成者**: コンテンツの登録や記事作成を行う（`UserDetail.is_uploader` / `is_author`）。
- **管理者**: 収集バッチの実行、Django管理サイトでのデータ整備、問い合わせ対応を行う。

## 主要機能

- **コンテンツフィード** (`/feed`): 動画・画像を縦スワイプで連続表示する。シリーズ単位で送り、`SeriesQueueItem` の重み付きキューで表示順を決める。タイプ（すべて/動画/画像/DMM動画/DMM画像）で絞り込める。
- **検索・タグ** (`/search`, `/tags`): キーワード・タグ・タイプでコンテンツを探す。
- **記事** (`/articles`, `/article/create`, `/article/[id]`): 複数コンテンツをまとめた記事を作成・閲覧する。サムネイルは動画の中間フレームから自動生成する。
- **ブログパーツ** (`/blog-parts`, `GET /api/blog-parts/`): 記事一覧のタイルを埋め込み用HTMLとして生成する。列数・行数・色・タイルサイズ・リンク先を指定できる。`make_blog_parts` バッチでファイルにも書き出せる。
- **クリック計測** (`ClickCount`, `/click-stats`): 外部リンクへの遷移をユーザー・リファラ・遷移先ごとに記録し、集計を表示する。
- **ソーシャル機能**: ブックマーク（公開/非公開フラグ付き）、フォロー、コメント、プロフィール。
- **Bot対策** (Cloudflare Turnstile): 初回アクセス時にダイアログで検証する。`NEXT_PUBLIC_TURNSTILE_ENABLED=false` で無効化できる。
- **問い合わせ** (`/contact`, `Inquiry`): フォーム送信内容をDBに保存し、`INQUIRY_RECIPIENT_EMAIL` へメール送信する。
- **広告枠** (`AdContent`): 任意の広告HTMLをタグ付きで登録し、`GET /api/ad-contents/` で配信する。
- **コンテンツ収集バッチ**: hime-channel / toxicstream / zettai-ero / DMM（FANZA）Affiliate API から動画・画像を取得する。一覧とオプションは [backend/tools/readme.md](../../backend/tools/readme.md)。

## コンテンツの扱い

- コンテンツは `Content`（id = `path + link + title` のSHA256先頭32文字）で一意に管理する。実体はローカルの `backend/media/` 配下、またはS3（`s3://` で始まる `path`）、もしくは外部URL（`link`）のいずれか。
- 長い動画は `split_video_as_short` で15秒ごとに分割し、同一 `series_id` のシリーズとして再登録する。フィードはこの短尺チャンクを前提としている。
- シリーズの表示頻度は `Series.weight`（`calc_series_weight` で対数スケール算出）→ `make_series_queue` でキュー化、の順で決まる。

## スコープ外

- コンテンツ自体の制作・課金・決済。
- 収集元サイトの認証が必要な領域からの取得。

具体的な機能の要件・設計・タスクは、機能ごとに [.kiro/specs/](../specs/README.md) 配下で管理する。プロダクトの前提が変わった場合はこのファイルを更新すること。
