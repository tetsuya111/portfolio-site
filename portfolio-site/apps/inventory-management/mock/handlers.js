// バックエンドのモック。portfolio-site の npm run build:apps が出力の HTML に差し込み、ブラウザで fetch を
// 横取りして応答する（バックエンドなしで S3 だけで動かすため）。portfolio-importer が雛形を作成した。
//
// portfolioMock.handle("GET", "/health", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("POST", "/auth/login", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("POST", "/auth/register", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("GET", "/users/me", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("GET", "/users", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("GET", "/products", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("POST", "/products", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("GET", "/products/:product_id", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("PUT", "/products/:product_id", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("DELETE", "/products/:product_id", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("POST", "/inventory/in", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("POST", "/inventory/out", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("GET", "/inventory/history", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});

portfolioMock.handle("GET", "/inventory/summary", (req) => {
  // 404 のまま（ログインできないため、ログイン後の画面は表示できない）
  return portfolioMock.notFound();
});
