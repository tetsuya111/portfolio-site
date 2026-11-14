# モックの既定の応答を 404 にし、500・通信エラーにしない

## 何を

- `portfolio-site/src/lib/mock-runtime.js`
  - `portfolioMock.notFound()`（404 の JSON）を追加した。
  - ハンドラーが例外を投げたときの応答を 500 から 404 に変えた。
  - `localhost`・`127.0.0.1`・`[::1]` 宛てで一致するハンドラーがない通信は、本物の fetch に回さず 404 で答えるようにした。
- `portfolios/portfolio-importer/importer/mock.py`: 雛形の各ハンドラーの既定の戻り値を `return {};` から `return portfolioMock.notFound();` に変えた。
- スキル `/add-portfolio` の「モックの仕上げ」の優先順位を変えた。正確なデータを書くことより、フロントエンドが呼ぶ API がすべて 404 で答えることを優先する。データは、404 では画面が表示できない箇所にだけ書く。
- 次のドキュメントを同じ方針に更新した: requirements.md（R1-10・R3-7〜R3-9・R5-1）、design.md、`portfolio-site/docs/apps.md`、importer の README。
- テストを追加・更新した（runtime 150件、importer 84件）。

## なぜ

ユーザーから「正確なデータを返すより、404 を返して internal server error にならないことを最優先にしてほしい」と要望があったため。

変更前の雛形の空オブジェクト `{}` は、フロントエンドが期待する形と合わないと、フロントエンド側で例外になりやすかった。ハンドラーの例外は 500 になっていた。開発時のバックエンド（localhost）への通信は、配信先では通信エラーになっていた。404 なら、多くのフロントエンドは「データなし」として扱える。
