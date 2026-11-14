# LINE BOTサーバーの design.md / tasks.md を作成

## 何を

`.kiro/specs/line-bot-server/` に design.md と tasks.md を新規作成した（requirements.md の8ストーリーに対する技術設計と、12タスクへの分解）。

- design.md: `line_bot/`（Python / FastAPI）をリポジトリの3つ目のアプリとして追加する。Webプロセスは署名検証と即時200のみ、機能の実行・LLM・Push送信はRedis + RQ のworkerで行う。データはBOT専用のPostgreSQL（`users` / `conversation_turns` / `processed_events`）。
- tasks.md: 土台（1-2）→ LLMなしで一周（3-6, 10）→ 対話（7-9）→ LIFF（11）→ ドキュメント（12）の順。

## なぜ

要件が固まったため、`.kiro/specs/README.md` の手順に従って設計とタスク分解に進んだ。

## 設計で決めたこと

- **DjangoのDBは共有しない**。契約状態は参照のみで、更新するコードをアプリに持たない。Django側にAPIを足す案は、Webサイトの変更がNon-Goalsであることと、障害の巻き込みを避けるため採らなかった。
- **重複排除は `processed_events` への INSERT の主キー違反で行う**（SELECT→INSERT だと再送が同時に届いたとき二重処理になりうる）。
- **非同期処理はRedis + RQ**。`BackgroundTasks` はプロセス再起動で消えるため要件（基準5）を満たさない。
- **クイックリプライはすべての返信に付ける**（requirements.md の未解決事項への回答）。依頼者が次にできることを常に選べ、サーバー側が状態を覚える必要もないため。
- **待機メッセージはreply、回答はPush**。replyは通数を消費しないため、1往復あたりのPushを1通に保てる。
- **長さ・Markdown・金額の抑制をプロンプトだけに頼らない**。送信前に整形し、金額表現を含む場合は案内文に差し替える。
- 登録はテキスト方式を先に作り、LIFFを後から足す（`LIFF_ID` の有無で案内を切り替え、登録処理は共通）。
- LLM呼び出しの上限は `DAILY_LLM_CALL_LIMIT`（既定30回/日・ユーザー）。

## 残っている未解決事項

実行環境（インフラ未定）、契約状態を誰が更新するか、対話プロンプトの作成時期、LIFFの利用可否、上限値30回の妥当性。いずれも段階2（LLMなしで一周させる）までの実装は止めない。

## 補足

実装は未着手。`line_bot/` ディレクトリもまだ作成していない。
