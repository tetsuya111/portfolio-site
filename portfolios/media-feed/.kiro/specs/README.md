# Specs（機能仕様）の運用ルール

新しい機能に着手する際は、実装より先にこのディレクトリ配下に仕様を作成する。1機能 = 1ディレクトリとし、次の3ファイルを順番に作成する。

```
.kiro/specs/<feature-slug>/
├── requirements.md   # 要件定義
├── design.md         # 技術設計
└── tasks.md          # 実装タスクの分解
```

`_template/` 配下に各ファイルの雛形があるので、新機能を始める際はコピーして使う。

## 進め方

1. **requirements.md を書く** — 課題・ゴール・Non-Goals・ユーザーストーリーと受け入れ基準を記述する。書き方は後述の「requirements.md の書き方」を参照。
2. **設計に進む前にrequirementsの内容を確認する** — 要件が固まっていない状態で設計・実装に進まない。
3. **design.md を書く** — データモデル、API、コンポーネント構成など、requirements.mdの要件を満たすための技術設計を記述する。既存の構成（[backend/readme.md](../../backend/readme.md)、[frontend/readme.md](../../frontend/readme.md)、[.kiro/steering/structure.md](../steering/structure.md)）との整合性を確認する。
4. **設計を確認してからtasksに進む** — 設計が固まっていない状態でタスク分解・実装に進まない。
5. **tasks.md を書く** — design.mdを実現するための実装タスクをチェックリスト形式で分解する。各タスクは独立して実行・検証できる粒度にする。
6. **タスクを1つずつ実装する** — tasks.mdのチェックリストを順に消化し、完了したタスクにはチェックを入れる。

## requirements.md の書き方

- **課題ドリブンで書く** — 「作りたいから作る」ではなく、誰のどんな課題を解決するのかから始める。
- **ユーザーストーリー** — `As a <ユーザー種別>, I want <したいこと>, so that <目的・理由>.` の形式で書く。実装手段ではなく、ユーザーにとっての価値を書く。
- **受け入れ基準はEARS記法で書く** — 条件と振る舞いを機械的に検証できる形にする。
  - ユビキタス: `THE SYSTEM SHALL <振る舞い>`
  - イベント駆動: `WHEN <条件> THE SYSTEM SHALL <振る舞い>`
  - 状態駆動: `WHILE <状態> THE SYSTEM SHALL <振る舞い>`
  - オプション: `WHERE <機能が存在する場合> THE SYSTEM SHALL <振る舞い>`
  - 分岐: `IF <条件> THEN THE SYSTEM SHALL <振る舞い>`
- **曖昧な表現を避ける** — 「高速に」「適切に」「使いやすく」「など」は使わず、数値・具体例に置き換える（例: 「一覧は50件ずつ返す」「3秒以内に初回描画する」）。
- **Non-Goals を必ず書く** — 意図的にスコープ外とすることを明記し、後からのスコープ拡大を防ぐ。

## 命名

`<feature-slug>` はケバブケースの短い名前とする（例: `age-verification`, `click-stats-export`, `secrets-to-env`）。

## 現在のspec

| slug | 内容 | 状態 |
| --- | --- | --- |
| [video-playback-performance](./video-playback-performance/requirements.md) | フィードの動画再生の遅さの改善（Range対応・CDN・キャッシュ・先読み） | requirements まで作成済み。design / tasks は未作成 |

## 既存機能の扱い

現在実装済みの機能（フィード、検索、記事、ブログパーツ、クリック計測、ソーシャル機能、収集バッチ）はspecを作らずに実装されている。仕様の一次情報は各 `readme.md` と [.kiro/steering/product.md](../steering/product.md) にある。既存機能を大きく変更する場合は、その変更分についてspecを作成する。

## 補助ドキュメント

3ファイル以外を置いてもよい。既存コードのボトルネック調査など、requirements の根拠となる調査結果は `investigation.md` として同じディレクトリに置き、requirements.md から参照する（例: [video-playback-performance/investigation.md](./video-playback-performance/investigation.md)）。
