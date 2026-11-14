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

// ---------------------------------------------------------------------------------------------
// フィードに流すサンプル動画。動画の URL（https://...）を MOCK_VIDEOS に手で書く。
// - src: 動画の URL（https:// で始まるもの。それ以外の行は無視する）。ブラウザが直接取得する。
// - title・poster（ポスター画像の https:// の URL）は省略できる。
// - 1件もなければ一覧の API は 404 を返し、フィードは空になる（画面は壊れない）。
// タイトル・ユーザー名・タグは公開されるため、架空のもの（サンプル・demo など）にすること。
// ---------------------------------------------------------------------------------------------
const MOCK_VIDEOS = [
  // { src: "https://example.com/media-feed/output_000.mp4", title: "サンプル動画 01" },
  // { src: "https://example.com/media-feed/output_001.mp4", poster: "https://example.com/media-feed/output_001.jpg" },
];

const isHttps = (u) => typeof u === "string" && u.startsWith("https://");

const MOCK_CONTENTS = MOCK_VIDEOS.filter((v) => v && isHttps(v.src)).map((v, i) => {
  const url = v.src;
  return {
    id: `mock-${i + 1}`,
    type: "video",
    title: v.title || `サンプル動画 ${String(i + 1).padStart(2, "0")}`,
    path: "",
    link: url,
    source_url: "",
    user: "demo",
    description: "ポートフォリオ用のサンプルです。",
    tags: [{ name: "サンプル" }],
    created_at: "2026-01-01T00:00:00Z",
    media_url: url,
    poster_url: isHttps(v.poster) ? v.poster : undefined,
  };
});

// コンテンツ一覧（フィード・検索）。絞り込み・ページングは再現せず、常に同じ一覧を返す。
// FeedPlayer は一覧が空の 200 だと描画のたびに再取得するため、0件のときは 404 にする。
portfolioMock.handle("GET", "/api/contents/", () =>
  MOCK_CONTENTS.length > 0
    ? { results: MOCK_CONTENTS, count: MOCK_CONTENTS.length }
    : portfolioMock.notFound());

// 以下はすべて 404 のまま。FeedPlayer・各画面は失敗を catch して「データなし」・エラー表示として扱う。
// コンテンツ
portfolioMock.handle("GET", "/api/contents/:id/", () => portfolioMock.notFound());
portfolioMock.handle("GET", "/api/contents/:id/related/", () => portfolioMock.notFound());
portfolioMock.handle("GET", "/api/tags/", () => portfolioMock.notFound());
portfolioMock.handle("GET", "/api/ad-contents/", () => portfolioMock.notFound());
// ユーザー・プロフィール
portfolioMock.handle("GET", "/api/users/", () => portfolioMock.notFound());
portfolioMock.handle("GET", "/api/profile/:username/", () => portfolioMock.notFound());
portfolioMock.handle("PUT", "/api/profile/:username/", () => portfolioMock.notFound());
// ブックマーク
portfolioMock.handle("GET", "/api/bookmarks/:username/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/bookmarks/:username/", () => portfolioMock.notFound());
portfolioMock.handle("DELETE", "/api/bookmarks/:username/:id/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/bookmarks/:username/download/", () => portfolioMock.notFound());
// フォロー
portfolioMock.handle("GET", "/api/following/:username/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/following/:username/", () => portfolioMock.notFound());
portfolioMock.handle("DELETE", "/api/following/:username/:target/", () => portfolioMock.notFound());
// コメント
portfolioMock.handle("GET", "/api/comments/:contentId/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/comments/:contentId/", () => portfolioMock.notFound());
portfolioMock.handle("PUT", "/api/comments/detail/:id/", () => portfolioMock.notFound());
portfolioMock.handle("DELETE", "/api/comments/detail/:id/", () => portfolioMock.notFound());
// 認証
portfolioMock.handle("POST", "/api/auth/register/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/auth/login/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/auth/token/refresh/", () => portfolioMock.notFound());
portfolioMock.handle("DELETE", "/api/auth/user/", () => portfolioMock.notFound());
portfolioMock.handle("GET", "/api/auth/me/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/auth/turnstile/", () => portfolioMock.notFound());
// 記事
portfolioMock.handle("GET", "/api/articles/", () => portfolioMock.notFound());
portfolioMock.handle("GET", "/api/articles/:id/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/articles/", () => portfolioMock.notFound());
portfolioMock.handle("DELETE", "/api/articles/:id/", () => portfolioMock.notFound());
portfolioMock.handle("GET", "/api/article-tags/", () => portfolioMock.notFound());
// ブログパーツ（BlogPartsCreateClient のプレビューが fetch で取得する）
portfolioMock.handle("GET", "/api/blog-parts/", () => portfolioMock.notFound());
// クリック集計・問い合わせ
portfolioMock.handle("GET", "/api/click-counts/", () => portfolioMock.notFound());
portfolioMock.handle("POST", "/api/inquiries/", () => portfolioMock.notFound());
