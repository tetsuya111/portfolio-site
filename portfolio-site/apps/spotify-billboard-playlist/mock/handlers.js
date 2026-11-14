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
//
// ログイン（/auth/login・/auth/callback）はページ遷移で行うため横取りできない。
// ログイン画面を出さないよう、/api/me は常にログイン済みのデモ利用者を返す。

// デモ用の架空の曲（実在のチャートデータではない）
const DEMO_TRACKS = [
  { title: "Midnight Signal", artist: "The Neon Hours" },
  { title: "Paper Skies", artist: "Lena Hart" },
  { title: "Golden Static", artist: "Northbound" },
  { title: "Run It Back", artist: "Kai Rivers" },
  { title: "Slow Motion Summer", artist: "Juniper & June" },
  { title: "Echo Park", artist: "Milo Grant" },
  { title: "Glass Heart", artist: "Avery Stone" },
  { title: "Velvet Rain", artist: "The Lanterns" },
  { title: "Heatwave Radio", artist: "Sol Mendez" },
  { title: "Last Train Home", artist: "Harbor Lights" },
];

portfolioMock.handle("GET", "/api/me", () => ({
  authenticated: true,
  id: "demo-user",
  display_name: "Demo User",
  csrf_token: "demo-csrf-token",
}));

portfolioMock.handle("POST", "/auth/logout", () => null);

portfolioMock.handle("POST", "/api/charts", (req) => ({
  id: 1,
  url: (req.body && req.body.url) || "https://billboard.mryogaku.com/",
  title: "ビルボード Hot 100（デモ）",
  tracks: DEMO_TRACKS.map((t, i) => ({ rank: i + 1, ...t })),
}));

portfolioMock.handle("POST", "/api/playlists", (req) => {
  const tracks = (req.body && Array.isArray(req.body.tracks)) ? req.body.tracks : [];
  // 最後の1曲は「見つからなかった曲」の表示例にする
  const notFound = tracks.length > 1 ? tracks.slice(-1) : [];
  return {
    playlist_id: "demo-playlist",
    url: "https://open.spotify.com/",
    added: tracks.length - notFound.length,
    not_found: notFound,
  };
});
