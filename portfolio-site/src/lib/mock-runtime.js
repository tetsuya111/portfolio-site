// ポートフォリオのフロントエンド（apps/<スラッグ>/）をバックエンドなしで動かすためのモックのランタイム。
// npm run build:apps が mock: true のアプリの HTML の <head> 直後に差し込み、ブラウザで同期的に実行される
// （アプリのスクリプトより先に動く）。window.fetch を差し替え、portfolioMock.handle で登録したメソッド・パスに
// 一致するリクエストには通信せずハンドラーの戻り値で応答する。依存パッケージを持たない。
(function () {
  "use strict";
  const script = document.currentScript;
  // アプリの配信パス（例 /apps/my-app）。相対パスで呼ばれた API もこれを除いたパスで一致させる
  const base = ((script && script.dataset && script.dataset.base) || "").replace(/\/+$/, "");
  const realFetch = window.fetch.bind(window);
  const handlers = [];
  // 横取りするオリジン: アプリと同じオリジンと、開発時のバックエンド（localhost）。外部の API はそのまま通信する
  const LOCAL_HOSTS = ["localhost", "127.0.0.1", "[::1]"];
  // 静的ファイルに見える区間（例 1.txt）。パスの引数には一致させない（静的ファイル・Next.js のページデータを横取りしない）
  const FILE_NAME = /\.(?:txt|json|js|mjs|css|html?|map|xml|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|wasm)$/i;

  function segments(path) {
    return path.replace(/\/+$/, "").split("/").filter((s) => s !== "");
  }

  function decode(segment) {
    try {
      return decodeURIComponent(segment);
    } catch {
      return segment; // 不正な % エスケープはそのまま渡す
    }
  }

  function match(pattern, path) {
    const actual = segments(path);
    if (pattern.length !== actual.length) return null;
    const params = {};
    for (let i = 0; i < pattern.length; i++) {
      if (pattern[i].startsWith(":")) {
        if (FILE_NAME.test(actual[i])) return null;
        params[pattern[i].slice(1)] = decode(actual[i]);
      }
      else if (pattern[i] !== actual[i]) return null;
    }
    return params;
  }

  function find(method, pathname) {
    const paths = [pathname];
    if (base && pathname.startsWith(base + "/")) paths.push(pathname.slice(base.length));
    for (const h of handlers) {
      if (h.method !== method) continue;
      for (const path of paths) {
        const params = match(h.pattern, path);
        if (params) return { handler: h, path: "/" + segments(path).join("/"), params };
      }
    }
    return null;
  }

  async function readBody(input, init, isRequest) {
    let text;
    if (init && init.body !== undefined && init.body !== null) text = await new Response(init.body).text();
    else if (isRequest) text = await input.clone().text();
    if (text === undefined || text === "") return undefined;
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }

  function toResponse(value) {
    if (value instanceof Response) return value;
    if (value === undefined || value === null) return new Response(null, { status: 204 });
    return new Response(JSON.stringify(value), { status: 200, headers: { "Content-Type": "application/json" } });
  }

  window.portfolioMock = {
    /** ハンドラーを登録する。path の「:名前」は任意の1区間に一致し、req.params に入る */
    handle(method, path, fn) {
      handlers.push({ method: String(method).toUpperCase(), pattern: segments(String(path)), fn });
    },
  };

  window.fetch = async function (input, init) {
    const isRequest = typeof Request !== "undefined" && input instanceof Request;
    const url = new URL(isRequest ? input.url : String(input), window.location.href);
    const method = String((init && init.method) || (isRequest ? input.method : "GET")).toUpperCase();
    const own = url.origin === window.location.origin || LOCAL_HOSTS.includes(url.hostname);
    const found = own ? find(method, url.pathname) : null;
    if (!found) return realFetch(input, init);
    try {
      const body = await readBody(input, init, isRequest);
      const value = await found.handler.fn({ method, path: found.path, params: found.params, query: url.searchParams, body });
      return toResponse(value);
    } catch (e) {
      console.error(`モックのハンドラーでエラーが発生しました（${method} ${url.pathname}）`, e);
      return new Response(JSON.stringify({ error: "mock handler failed" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  };
})();
