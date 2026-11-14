// バックエンドのモック。portfolio-site の npm run build:apps が出力の HTML に差し込み、ブラウザで fetch を
// 横取りして応答する（バックエンドなしで S3 だけで動かすため）。portfolio-importer が雛形を作成した。
//
// portfolioMock.handle(メソッド, パス, (req) => 応答) で登録する。
// - パスの「:名前」は任意の1区間に一致し、req.params.名前 に入る。
// - req = { method, path, params, query（URLSearchParams）, body（JSON なら変換済み） }
// - 戻り値: オブジェクトなど → 200 の JSON / undefined・null → 204 / new Response(...) → そのまま。async も可。
// - 既定は portfolioMock.notFound()（404）。正確なデータより、500（サーバーエラー）にしないことを優先する。
//   ハンドラーが例外を投げても 404 になる。localhost 宛てで一致しない通信も 404 になる。
// - このファイルは公開されるため、秘密情報を書かないこと。

// ルートを検出できなかったため、フロントエンドが呼ぶ API に合わせて書き足すこと。例:
// portfolioMock.handle("GET", "/api/items/:id", (req) => {
//   return { id: req.params.id, name: "サンプル" };
// });

// フロントエンド（src/lib/api.ts・ChatScreen・管理者画面）が呼ぶ API。すべて 404 のまま。
// api.ts は失敗を ApiError として画面内のエラー表示・未ログイン扱いにするため、404 でも画面は白くならない。
// 認証
portfolioMock.handle("POST", "/api/auth/refresh/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/auth/google/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/auth/dev-login/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/auth/logout/", () => portfolioMock.notFound());
// 対話画面
portfolioMock.handle("GET", "/api/me/", () => portfolioMock.notFound());
portfolioMock.handle("GET", "/api/conversation/", () => portfolioMock.notFound());
portfolioMock.handle("GET", "/api/templates/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/conversation/messages/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/conversation/actions/:key/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/conversation/clear/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/summaries/:id/submit/", () => portfolioMock.notFound());
// 管理者画面
portfolioMock.handle("GET", "/api/admin/summaries/", () => portfolioMock.notFound());
portfolioMock.handle("GET", "/api/admin/summaries/:id/", () => portfolioMock.notFound());
portfolioMock.handle("PATCH", "/api/admin/summaries/:id/", () => portfolioMock.notFound());
