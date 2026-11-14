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
    expect(init.headers["Content-Type"]).toBe("application/json");
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
