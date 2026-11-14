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
// フィードに流すサンプル動画。実体は portfolio-site/apps/media-feed/public/mock-media/ に手で置く
// （git-lfs で管理する。置き方は同ディレクトリの README.md）。ファイルがなくても画面は壊れず、
// 動画が再生されないだけになる。ファイルを増やしたら、ここに1行足す。
// タイトル・ユーザー名・タグは公開されるため、架空のもの（サンプル・demo など）にすること。
// ---------------------------------------------------------------------------------------------
const MEDIA_BASE = "/apps/media-feed/mock-media/";
const MOCK_MEDIA = [
  { type: "video", file: "sample01.mp4", poster: "sample01.jpg", title: "サンプル動画 01" },
  { type: "video", file: "sample02.mp4", poster: "sample02.jpg", title: "サンプル動画 02" },
  { type: "video", file: "sample03.mp4", poster: "sample03.jpg", title: "サンプル動画 03" },
];

const MOCK_CONTENTS = MOCK_MEDIA.map((m, i) => ({
  id: `mock-${i + 1}`,
  type: m.type,
  title: m.title,
  path: "",
  link: MEDIA_BASE + m.file,
  source_url: "",
  user: "demo",
  description: "ポートフォリオ用のサンプルです。",
  tags: [{ name: "サンプル" }],
  created_at: "2026-01-01T00:00:00Z",
  media_url: MEDIA_BASE + m.file,
  poster_url: m.poster ? MEDIA_BASE + m.poster : undefined,
}));

// コンテンツ一覧（フィード・検索）。絞り込み・ページングは再現せず、常に同じ一覧を返す。
// FeedPlayer は一覧が空だと描画のたびに再取得するため、空の結果は返さない。
portfolioMock.handle("GET", "/api/contents/", () => ({ results: MOCK_CONTENTS, count: MOCK_CONTENTS.length }));

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
