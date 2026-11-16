# 在庫管理システム 要件定義（requirements.md）

## 前提と仮定

依頼者への確認を行わずに作成したため、次の点は推定で決めた。後から覆す場合は design.md・tasks.md もあわせて見直す。

- **配置**: 依頼の「`portfolios/` 以下以外は修正しない」に従い、プロジェクト・設計ファイル・作業ログをすべて `portfolios/inventory-management/` 配下に置く（リポジトリ標準の `docs/specs/`・ルートの `logs/` は使わない）。
- **権限区分**: 「管理者（admin）」と「一般ユーザー（staff）」の2種類とする。ユーザー登録と商品の削除は管理者のみ、それ以外の操作は両者に許可する。
- **ユーザー登録**: 誰でも自己登録できる公開登録にはせず、管理者が登録する（業務システムのため）。最初の管理者はコマンドで作成する。
- **商品の削除**: 論理削除とし、入出庫履歴は削除後も参照できる。削除済み商品の商品コードは再利用できない。
- **商品の項目**: 商品コード・商品名・カテゴリ（自由入力の文字列）・単位・単価・発注点（在庫が少ないと判断する閾値）・説明。
- **在庫数**: 入出庫でのみ増減し、商品の更新 API では変更できない。数量は1以上の整数。
- **記録の訂正**: 登録済みの入出庫記録の編集・取消は MVP に含めない（逆方向の記録を追加して訂正する運用とする）。
- **トークン**: アクセストークンのみ（リフレッシュトークンなし）、有効期限60分。ログアウトはクライアント側でトークンを破棄する。
- **商品カテゴリ・運用ルール**: 依頼者側タスク（ヒアリング回答）が未実施のため、一般的な小売・倉庫を想定した汎用の項目にする。
- **依頼者側のタスク**（レビュー・受け入れ確認など）はシステムの要件ではないため、本書の対象外とする。

## 背景・課題

- 就職・転職活動や実績提示のためのポートフォリオとして、業務システム（在庫管理システム）を開発する。実用性よりも「設計力・実装力・技術スタックの扱い」が見えることを重視する。
- 小規模な事業者では、在庫を表計算ソフトや紙で管理していることが多く、「誰が・いつ・何を・いくつ動かしたか」が残らない、同時に更新すると数が合わなくなる、という課題がある。
- 技術スタックは フロントエンド: Next.js（React）+ TypeScript、バックエンド: FastAPI + SQLAlchemy + Alembic に固定する（技術選定自体が訴求点）。
- 開発期間約1か月・予算約20万円のため、MVP としてスコープを絞る。

## 成功指標

- ゴール（最低基準）の受け入れ基準（REQ-PRD-*・REQ-INV-*）がすべて自動テストで成功する。
- 入出庫を任意の順序で行ったあと、すべての商品で「在庫数 = 入庫数量の合計 − 出庫数量の合計」かつ「在庫数 ≥ 0」が成り立つ（並行出庫のテストを含む）。
- 新しい開発者が README の手順だけで、10分以内に開発環境を起動してログインできる。
- バックエンド・フロントエンドのテスト・lint・ビルドがコマンド1つ（`npm test`・`npm run lint`・`npm run build`）で成功する。

## ユーザーストーリー

- US-1: As a 在庫担当者, I want 自分のアカウントでログイン・ログアウトしたい, so that 自分の名前で操作が記録され、他人に操作されない.
- US-2: As a 管理者, I want 利用者のアカウントを作り権限区分を設定したい, so that 複数人が個別に作業でき、危険な操作を管理者に限定できる.
- US-3: As a 在庫担当者, I want 商品を登録・確認・修正・削除したい, so that 入出庫を記録する商品を正しく管理できる.
- US-4: As a 在庫担当者, I want 入庫・出庫を記録したい, so that 現在の在庫数が実際の在庫と一致する.
- US-5: As a 在庫担当者, I want 入出庫の履歴を絞り込んで見たい, so that 在庫数が変わった理由を追跡できる.
- US-6: As a 在庫担当者, I want 商品ごとの在庫数を一覧で見たい, so that 在庫の過不足をすぐに把握できる.
- US-7: As a 在庫担当者, I want ログイン直後に在庫状況の概要を見たい, so that 在庫の少ない商品や最近の動きを素早く把握できる.

## 機能要件

### 認証（REQ-AUTH）— US-1

- REQ-AUTH-1: WHEN 有効なユーザーが正しいユーザー名とパスワードでログインした THE SYSTEM SHALL アクセストークン（JWT）を返す。
- REQ-AUTH-2: IF ユーザー名またはパスワードが誤っている THEN THE SYSTEM SHALL 401 を返し、どちらが誤っているかを区別しないメッセージを返す。
- REQ-AUTH-3: IF 無効化されたユーザーがログインした THEN THE SYSTEM SHALL 401 を返す。
- REQ-AUTH-4: WHEN 有効なトークンでログインユーザー情報を取得した THE SYSTEM SHALL ID・ユーザー名・権限区分を返し、パスワードのハッシュを返さない。
- REQ-AUTH-5: IF トークンがない・署名が不正・期限切れのいずれかで保護された API を呼んだ THEN THE SYSTEM SHALL 401 を返す。
- REQ-AUTH-6: THE SYSTEM SHALL ログイン・ヘルスチェック以外のすべての API を保護する。
- REQ-AUTH-7: WHEN 画面でログアウトした THE SYSTEM SHALL 保持しているトークンを破棄してログイン画面を表示する。
- REQ-AUTH-8: WHEN 未ログインの状態でログイン画面以外を開いた THE SYSTEM SHALL ログイン画面を表示する。

### ユーザー管理（REQ-USR）— US-2

- REQ-USR-1: WHEN 管理者がユーザー名・パスワード・権限区分を指定して登録した THE SYSTEM SHALL ユーザーを作成し、作成したユーザーでログインできる。
- REQ-USR-2: IF 一般ユーザーがユーザーを登録しようとした THEN THE SYSTEM SHALL 403 を返し、ユーザーを作成しない。
- REQ-USR-3: IF 既に使われているユーザー名で登録した THEN THE SYSTEM SHALL 409 を返す。
- REQ-USR-4: IF ユーザー名が3〜50文字の英数字・`_`・`-` でない、またはパスワードが8文字未満である THEN THE SYSTEM SHALL 422 を返す。
- REQ-USR-5: WHEN 管理者がユーザー一覧を開いた THE SYSTEM SHALL 登録済みユーザーのユーザー名・権限区分・作成日時を表示する。
- REQ-USR-6: THE SYSTEM SHALL 初期の管理者ユーザーをコマンドで作成する手段を持つ。
- REQ-USR-7: THE SYSTEM SHALL パスワードをハッシュ化して保存する。

### 商品マスタ（REQ-PRD）— US-3

- REQ-PRD-1: WHEN 商品コード・商品名を含む正しい値で商品を登録した THE SYSTEM SHALL 在庫数0の商品を作成して返す。
- REQ-PRD-2: IF 既存（削除済みを含む）の商品コードで登録・更新した THEN THE SYSTEM SHALL 409 を返し、商品を変更しない。
- REQ-PRD-3: IF 必須項目の欠落・文字数超過・負の単価や発注点がある THEN THE SYSTEM SHALL 422 を返す。
- REQ-PRD-4: WHEN 商品一覧を取得した THE SYSTEM SHALL 削除されていない商品を商品コード順に返す。
- REQ-PRD-5: WHEN キーワードを指定して商品一覧を取得した THE SYSTEM SHALL 商品コードまたは商品名にキーワードを含む商品だけを返す。
- REQ-PRD-6: WHEN 商品の詳細を取得した THE SYSTEM SHALL 現在の在庫数を含む商品情報を返す。
- REQ-PRD-7: WHEN 商品を更新した THE SYSTEM SHALL 在庫数以外の項目を更新する。
- REQ-PRD-8: WHEN 管理者が商品を削除した THE SYSTEM SHALL その商品を一覧・詳細・在庫集計から除外し、入出庫履歴には残す。
- REQ-PRD-9: IF 一般ユーザーが商品を削除しようとした THEN THE SYSTEM SHALL 403 を返す。
- REQ-PRD-10: IF 存在しない・削除済みの商品の詳細取得・更新・削除をした THEN THE SYSTEM SHALL 404 を返す。

### 入出庫の記録（REQ-INV）— US-4

- REQ-INV-1: WHEN 商品と1以上の整数の数量で入庫を登録した THE SYSTEM SHALL 入庫記録を作成し、在庫数を数量分増やす。
- REQ-INV-2: WHEN 在庫数以下の数量で出庫を登録した THE SYSTEM SHALL 出庫記録を作成し、在庫数を数量分減らす。
- REQ-INV-3: IF 在庫数を超える数量で出庫を登録した THEN THE SYSTEM SHALL 409 を返し、記録を作成せず在庫数も変えない。
- REQ-INV-4: IF 数量が1未満・整数でない・上限（1,000,000）超過である THEN THE SYSTEM SHALL 422 を返す。
- REQ-INV-5: IF 存在しない・削除済みの商品を指定した THEN THE SYSTEM SHALL 404 を返す。
- REQ-INV-6: WHILE 同じ商品に対して複数の出庫が同時に行われている THE SYSTEM SHALL 在庫数を0未満にしない。
- REQ-INV-7: THE SYSTEM SHALL 各記録に商品・区分（入庫／出庫）・数量・登録後の在庫数・操作したユーザー・日時・備考を保存する。

### 入出庫履歴（REQ-HIS）— US-5

- REQ-HIS-1: WHEN 履歴を取得した THE SYSTEM SHALL 記録を新しい順に、商品コード・商品名・区分・数量・登録後の在庫数・操作したユーザー名・日時・備考とともに返す。
- REQ-HIS-2: WHEN 商品・区分・期間（開始日・終了日）を指定した THE SYSTEM SHALL すべての条件に合う記録だけを返す。
- REQ-HIS-3: WHEN 件数と開始位置を指定した THE SYSTEM SHALL その範囲の記録と、条件に合う全件数を返す（既定20件、最大100件）。
- REQ-HIS-4: THE SYSTEM SHALL 削除済みの商品の記録も履歴に含める。

### 在庫集計（REQ-SUM）— US-6

- REQ-SUM-1: WHEN 在庫集計を取得した THE SYSTEM SHALL 削除されていない各商品の在庫数・発注点・在庫が少ないかどうかを返す。
- REQ-SUM-2: THE SYSTEM SHALL 各商品の在庫数を、その商品の入庫数量の合計から出庫数量の合計を引いた値と一致させる。
- REQ-SUM-3: THE SYSTEM SHALL 在庫数が発注点以下の商品を「在庫が少ない」と判定する。
- REQ-SUM-4: THE SYSTEM SHALL 商品数・総在庫数・在庫が少ない商品の数を集計値として返す。
- REQ-SUM-5: WHEN 在庫一覧画面で在庫数の列を選んだ THE SYSTEM SHALL 在庫数の昇順・降順で並び替える。

### ダッシュボード（REQ-DSH）— US-7

- REQ-DSH-1: WHEN ログインした THE SYSTEM SHALL ダッシュボードをトップ画面として表示する。
- REQ-DSH-2: THE SYSTEM SHALL ダッシュボードに商品数・総在庫数・在庫が少ない商品の数を表示する。
- REQ-DSH-3: THE SYSTEM SHALL ダッシュボードに在庫が少ない商品の一覧を表示する。
- REQ-DSH-4: THE SYSTEM SHALL ダッシュボードに直近5件の入出庫記録を表示する。
- REQ-DSH-5: THE SYSTEM SHALL ダッシュボードに在庫数の多い上位10商品の在庫数を棒グラフで表示する。
- REQ-DSH-6: IF 商品・記録が1件もない THEN THE SYSTEM SHALL エラーにせず「データがありません」と表示する。

## 非機能要件

- NFR-SEC-1: THE SYSTEM SHALL JWT を HS256 で署名し、秘密鍵を環境変数から読み込む。
- NFR-SEC-2: IF 本番環境（`APP_ENV=production`）で秘密鍵が未設定または32文字未満である THEN THE SYSTEM SHALL 起動を中止する。
- NFR-SEC-3: THE SYSTEM SHALL CORS で許可するオリジンを環境変数で指定したものに限定する。
- NFR-SEC-4: THE SYSTEM SHALL 秘密情報（秘密鍵・DB ファイル・`.env`）をリポジトリに含めない。
- NFR-ENV-1: THE SYSTEM SHALL DB の接続先・秘密鍵・トークン有効期限・CORS・API の URL を環境変数で切り替え、開発用と本番用の設定を分けられる。
- NFR-ENV-2: THE SYSTEM SHALL 空の DB に対してマイグレーションでテーブルを作成できる。
- NFR-ENV-3: THE SYSTEM SHALL バックエンドを Docker イメージとして起動できる。
- NFR-ENV-4: THE SYSTEM SHALL フロントエンドを静的ファイルとして出力でき、サブパス（例: `/apps/inventory-management/`）配下で配信できる。
- NFR-QA-1: THE SYSTEM SHALL バックエンドの各 API の正常系・異常系を自動テストで確認する。
- NFR-QA-2: THE SYSTEM SHALL `npm test`・`npm run lint`・`npm run build` でバックエンド・フロントエンドの両方を検証できる。
- NFR-DOC-1: THE SYSTEM SHALL 日本語の README に構成・起動手順・テスト方法・デモ用アカウントの作り方を書く。
- NFR-DOC-2: THE SYSTEM SHALL API 仕様を OpenAPI（`/docs`）で参照でき、構成図・ER 図を含む設計資料を持つ。
- NFR-UI-1: THE SYSTEM SHALL 幅375pxの画面でも横スクロールなしで主要な操作ができる。

## Non-Goals

- リフレッシュトークン・サーバー側でのトークン失効・ログイン試行回数の制限
- パスワードリセット・メール認証・ソーシャルログイン・ユーザーの編集／削除画面
- 操作ごと・カテゴリごとの細かい権限管理（将来拡張の候補）
- 在庫アラートの通知（将来拡張の候補。今回は発注点による「在庫が少ない」の表示まで）
- CSV エクスポート・一括登録（将来拡張の候補）
- 入出庫記録の編集・取消、複数倉庫・ロット・賞味期限の管理、在庫金額の評価
- 本番環境への実際のデプロイ（VPS・S3 への登録）と portfolio-site への掲載（`portfolios/` 外の変更を伴うため別作業）
- CI/CD の構築
