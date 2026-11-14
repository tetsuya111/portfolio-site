# 要件定義: 取り込んだフロントエンドの URL をサイト内の相対パスで保存する

元の要望: [issue #21](https://github.com/tetsuya111/portfolio-site/issues/21)
関連: [add-portfolio の要件](../add-portfolio/requirements.md)

## 前提と仮定

無人実行のため、issue・既存コードから次のとおり判断した。覆したい場合はこの節を起点に修正する。

| # | 仮定 | 根拠 |
|---|---|---|
| A1 | `--site-url` は廃止せず、指定したときだけ従来どおり絶対 URL（`<URL>/apps/<スラッグ>/`）を保存する。未指定なら相対パス `/apps/<スラッグ>/` を保存する | 絶対 URL で保存したい運用を残しつつ、既定を issue の要望に合わせる。既存の呼び出し方が壊れない |
| A2 | `/add-portfolio` スキルは、ドメインを探して `--site-url` を付ける手順をやめ、既定では付けない | 付けると本番のドメインが掲載 md に入り、issue の課題がそのまま残るため |
| A3 | サイト内のパスとして受け付けるのは、`/` で始まり、2文字目が `/`・`\` でなく、空白・制御文字・`\` を含まない文字列とする | `//host`・`/\host` はブラウザが別ホストとして解釈する。`\` はブラウザが `/` に読み替える |
| A4 | 相対パスの受け付けは `portfolioSchema` の `url` のみに入れる。`profileSchema` の `links` は http(s) のまま | issue の Non-Goals |
| A5 | `portfolio:new` CLI・管理画面も `portfolioSchema` を共有するため、相対パスを受け付けるようになる。これは許容する | 同じ掲載 md を書く経路で判定をそろえる（schemas.ts の方針） |
| A6 | リンクは相対パスでも `target="_blank"` のまま新しいタブで開く | 表示を変えずに済み、アプリを開いてもサイトの閲覧位置が残る |
| A7 | 元のプロジェクトのメタデータ（`portfolios/docs/<スラッグ>.md`）の `url` は、従来どおり http(s) のみ採用する | issue の受け入れ基準4 |

## 背景・課題

`--site-url` を付けないと掲載 md に `url` が入らず、付けると本番のドメインが書かれるため、dev のサイトから dev に配信したフロントエンドを開けない。importer・サイトのスキーマとも http(s) の URL しか受け付けない。

## ゴール

- フロントエンドを配信登録すると、`--site-url` なしで掲載 md に `url: "/apps/<スラッグ>/"` が入り、本番・dev どちらのサイトでも表示中のドメインのアプリが開く。

## Non-Goals（やらないこと）

- 取り込み済みの掲載 md（`spotify-billboard-playlist.md` など）の書き換え
- `url` 以外のリンク（本文中のリンク、`profile.md` の `links`）の相対パス対応
- dev と本番のドメインの切り替え（ビルド時の環境変数など）

## 成功指標

- `add_portfolio.py <パス>` で Vite のフロントエンドを取り込むと、掲載 md に `url: "/apps/<スラッグ>/"` が入り、`npm run build` が成功してタイルのボタンの `href` が `/apps/<スラッグ>/` になる。

## ユーザーストーリー

- As a サイト運営者, I want 取り込んだフロントエンドへのリンクをドメインなしで保存したい, so that 本番でも dev でも、それぞれの環境に配信したフロントエンドが開く。

## 機能要件（受け入れ基準）

### importer（portfolios/portfolio-importer）

- **R1-1**: WHEN フロントエンドを `apps.json` に配信登録し、`--site-url` を指定していない THE SYSTEM SHALL 掲載 md の `url` に `/apps/<スラッグ>/` を保存する。
- **R1-2**: WHEN フロントエンドを配信登録し、`--site-url` を指定した THE SYSTEM SHALL 従来どおり `<site-url>/apps/<スラッグ>/` を保存する。
- **R1-3**: WHILE フロントエンドを配信登録しなかった THE SYSTEM SHALL 元のプロジェクトのメタデータにある http(s) の URL を `url` に使い、http(s) 以外（相対パスを含む）は使わない。

### スキーマと表示（portfolio-site）

- **R2-1**: WHEN 掲載 md の `url` が A3 を満たすサイト内のパスである THE SYSTEM SHALL `portfolioSchema` の検証を通す。
- **R2-2**: IF `url` が `//` または `/\` で始まる、空白・`\` を含む、または http(s) 以外のスキーム（`javascript:` など）である THEN THE SYSTEM SHALL 検証エラーにする。
- **R2-3**: WHEN `url` がサイト内のパスである THE SYSTEM SHALL タイルと詳細ページのボタンのリンク先をそのパスにする。

### スキル・ドキュメント

- **R3-1**: `/add-portfolio` スキルと importer の README は、`--site-url` が任意で、未指定なら相対パスになることを記載する。

## 非機能要件

- Python は標準ライブラリのみ（既存方針）。
- 既存の http(s) の `url` を持つ掲載 md は引き続き検証を通る。
