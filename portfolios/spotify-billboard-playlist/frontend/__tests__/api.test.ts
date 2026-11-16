import { describe, expect, it, vi } from "vitest";
import { ApiError, createPlaylist, fetchChart, getMe, logout } from "@/lib/api";

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

/** 呼ぶたびに新しい Response を返す（同じ Response は一度しか読めないため）。 */
function mockFetchSequence(...responses: [number, unknown][]) {
  let i = 0;
  const fn = vi.fn().mockImplementation(async () => {
    const [status, body] = responses[Math.min(i++, responses.length - 1)];
    return new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

const LOGGED_IN = { authenticated: true, id: "u1", display_name: "Tetsu", csrf_token: "tok" };

describe("csrf token", () => {
  it("getMe 後の POST に X-CSRF-Token が付く", async () => {
    const fn = mockFetchSequence([200, LOGGED_IN], [200, { id: 1, url: "u", title: "", tracks: [] }]);
    await getMe();
    await fetchChart("https://billboard.mryogaku.com/");
    const [, init] = fn.mock.calls[1];
    expect(new Headers(init.headers).get("X-CSRF-Token")).toBe("tok");
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("logout にも X-CSRF-Token が付く", async () => {
    const fn = mockFetchSequence([200, LOGGED_IN], [204, undefined]);
    await getMe();
    await logout();
    expect(new Headers(fn.mock.calls[1][1].headers).get("X-CSRF-Token")).toBe("tok");
  });

  it("未ログインなら X-CSRF-Token を付けない", async () => {
    const fn = mockFetchSequence([200, LOGGED_IN], [200, { authenticated: false }], [204, undefined]);
    await getMe();
    await getMe();
    await logout();
    expect(new Headers(fn.mock.calls[2][1].headers).get("X-CSRF-Token")).toBeNull();
  });

  it("logout 後はトークンを送らない", async () => {
    const fn = mockFetchSequence([200, LOGGED_IN], [204, undefined], [200, { id: 1, url: "u", tracks: [] }]);
    await getMe();
    await logout();
    await fetchChart("x");
    expect(new Headers(fn.mock.calls[2][1].headers).get("X-CSRF-Token")).toBeNull();
  });

  it("GET には付けない", async () => {
    const fn = mockFetchSequence([200, LOGGED_IN], [200, LOGGED_IN]);
    await getMe();
    await getMe();
    expect(new Headers(fn.mock.calls[1][1].headers).get("X-CSRF-Token")).toBeNull();
  });
});

describe("csrf retry", () => {
  it("403 のときトークンを取り直して1回だけ再送する", async () => {
    const fn = mockFetchSequence(
      [200, LOGGED_IN],
      [403, { detail: "不正なリクエストです（CSRFトークン）" }],
      [200, { ...LOGGED_IN, csrf_token: "new" }],
      [200, { id: 1, url: "u", title: "", tracks: [] }],
    );
    await getMe();
    await expect(fetchChart("https://billboard.mryogaku.com/")).resolves.toMatchObject({ id: 1 });
    expect(fn).toHaveBeenCalledTimes(4);
    expect(new Headers(fn.mock.calls[3][1].headers).get("X-CSRF-Token")).toBe("new");
  });

  it("トークンが変わらなければ再送せず 403 を返す", async () => {
    const fn = mockFetchSequence(
      [200, LOGGED_IN],
      [403, { detail: "許可されていないオリジンです" }],
      [200, LOGGED_IN],
    );
    await getMe();
    const err = await fetchChart("x").catch((e) => e);
    expect(err.status).toBe(403);
    expect(fn).toHaveBeenCalledTimes(3);
  });
});

describe("csrf retry across accounts", () => {
  it("別のアカウントに切り替わっていたら再送しない", async () => {
    const fn = mockFetchSequence(
      [200, LOGGED_IN],
      [403, { detail: "不正なリクエストです（CSRFトークン）" }],
      [200, { ...LOGGED_IN, id: "u2", csrf_token: "other" }],
    );
    await getMe();
    const err = await createPlaylist("n", [{ title: "t", artist: "a" }]).catch((e) => e);
    expect(err.status).toBe(403);
    expect(fn).toHaveBeenCalledTimes(3);
  });
});

describe("api", () => {
  it("getMe returns the parsed body", async () => {
    mockFetch(200, { authenticated: true, id: "u1", display_name: "Tetsu" });
    await expect(getMe()).resolves.toEqual({ authenticated: true, id: "u1", display_name: "Tetsu" });
  });

  it("fetchChart posts the url as JSON", async () => {
    const fn = mockFetch(200, { id: 1, url: "u", title: "", tracks: [] });
    await fetchChart("https://billboard.mryogaku.com/");
    const [path, init] = fn.mock.calls[0];
    expect(path).toBe("/api/charts");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ url: "https://billboard.mryogaku.com/" });
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("createPlaylist posts name and tracks", async () => {
    const fn = mockFetch(201, { playlist_id: "p", url: "x", added: 1, not_found: [] });
    await createPlaylist("n", [{ title: "t", artist: "a" }]);
    const [path, init] = fn.mock.calls[0];
    expect(path).toBe("/api/playlists");
    expect(JSON.parse(init.body)).toEqual({ name: "n", tracks: [{ title: "t", artist: "a" }] });
  });

  it("logout accepts 204 without body", async () => {
    mockFetch(204, undefined);
    await expect(logout()).resolves.toBeUndefined();
  });

  it("throws ApiError with backend detail", async () => {
    mockFetch(400, { detail: "billboard.mryogaku.com のURLのみ指定できます" });
    const err = await fetchChart("x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(400);
    expect(err.message).toBe("billboard.mryogaku.com のURLのみ指定できます");
  });

  it("formats validation (422) detail arrays", async () => {
    mockFetch(422, { detail: [{ msg: "String should have at most 2048 characters" }] });
    const err = await fetchChart("x").catch((e) => e);
    expect(err.message).toContain("2048");
  });

  it("falls back to a generic message for non-JSON errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Bad Gateway", { status: 502 })));
    const err = await getMe().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toContain("502");
  });

  it("wraps network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const err = await getMe().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
  });
});
