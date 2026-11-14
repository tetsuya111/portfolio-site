import { readFileSync } from "node:fs";
import { join } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

const code = readFileSync(join(__dirname, "..", "src", "lib", "mock-runtime.js"), "utf8");

interface MockWindow {
  location: { href: string; origin: string };
  fetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
  portfolioMock: {
    handle: (method: string, path: string, fn: (req: any) => unknown) => void;
    notFound: () => Response;
  };
}

/** ランタイムを偽の window・document で実行し、window を返す */
function load(base = "/apps/my-app") {
  const realFetch = vi.fn(async () => new Response("real"));
  const win = { location: { href: "https://example.com/apps/my-app/", origin: "https://example.com" }, fetch: realFetch } as unknown as MockWindow;
  const doc = { currentScript: { dataset: { base } } };
  new Function("window", "document", code)(win, doc);
  return { win, realFetch };
}

describe("mock-runtime", () => {
  let win: MockWindow;
  let realFetch: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    ({ win, realFetch } = load());
  });

  it("answers a matching GET with JSON 200 without calling the real fetch", async () => {
    win.portfolioMock.handle("GET", "/api/me", () => ({ name: "Demo" }));
    const res = await win.fetch("/api/me");
    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toBe("application/json");
    expect(await res.json()).toEqual({ name: "Demo" });
    expect(realFetch).not.toHaveBeenCalled();
  });

  it("answers 204 when the handler returns nothing", async () => {
    win.portfolioMock.handle("post", "/auth/logout", () => undefined);
    const res = await win.fetch("/auth/logout", { method: "POST" });
    expect(res.status).toBe(204);
  });

  it("returns a Response from the handler as is", async () => {
    win.portfolioMock.handle("GET", "/api/x", () => new Response("nope", { status: 401 }));
    const res = await win.fetch("/api/x");
    expect(res.status).toBe(401);
    expect(await res.text()).toBe("nope");
  });

  it("passes params, query and the JSON body to the handler", async () => {
    const seen: any[] = [];
    win.portfolioMock.handle("POST", "/api/items/:id", async (req) => {
      seen.push(req);
      return { ok: true };
    });
    const res = await win.fetch("/api/items/42/?q=a", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "x" }),
    });
    expect(await res.json()).toEqual({ ok: true });
    expect(seen[0].method).toBe("POST");
    expect(seen[0].path).toBe("/api/items/42");
    expect(seen[0].params).toEqual({ id: "42" });
    expect(seen[0].query.get("q")).toBe("a");
    expect(seen[0].body).toEqual({ name: "x" });
  });

  it("passes a non-JSON body as text and accepts a Request object", async () => {
    let body: unknown;
    win.portfolioMock.handle("PUT", "/api/raw", (req) => {
      body = req.body;
      return null;
    });
    const res = await win.fetch(new Request("https://example.com/api/raw", { method: "PUT", body: "plain" }));
    expect(res.status).toBe(204);
    expect(body).toBe("plain");
  });

  it("matches a path under the app base and local development origins", async () => {
    win.portfolioMock.handle("GET", "/api/me", () => ({ ok: 1 }));
    expect(await (await win.fetch("api/me")).json()).toEqual({ ok: 1 });
    expect(await (await win.fetch("http://localhost:8000/api/me")).json()).toEqual({ ok: 1 });
    expect(await (await win.fetch("http://127.0.0.1:8000/api/me")).json()).toEqual({ ok: 1 });
    expect(realFetch).not.toHaveBeenCalled();
  });

  it("does not intercept other origins", async () => {
    win.portfolioMock.handle("GET", "/users/:id", () => ({}));
    expect(await (await win.fetch("https://api.github.com/users/octocat")).text()).toBe("real");
  });

  it("does not match a file name with a path parameter", async () => {
    win.portfolioMock.handle("GET", "/items/:id", (req) => ({ id: req.params.id }));
    expect(await (await win.fetch("/apps/my-app/items/1.txt?_rsc=x")).text()).toBe("real");
    expect(await (await win.fetch("/items/1")).json()).toEqual({ id: "1" });
    expect(await (await win.fetch("/items/john.doe")).json()).toEqual({ id: "john.doe" });
  });

  it("uses the real fetch when nothing matches", async () => {
    win.portfolioMock.handle("POST", "/api/me", () => ({}));
    win.portfolioMock.handle("GET", "/api/items/:id", () => ({}));
    for (const url of ["/api/me", "/api/other", "/api/items/1/extra"]) {
      expect(await (await win.fetch(url)).text()).toBe("real");
    }
    expect(realFetch).toHaveBeenCalledTimes(3);
  });

  it("answers 404 instead of 500 when the handler throws", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    win.portfolioMock.handle("GET", "/api/boom", () => {
      throw new Error("boom");
    });
    win.portfolioMock.handle("GET", "/api/reject", async () => Promise.reject(new Error("x")));
    expect((await win.fetch("/api/boom")).status).toBe(404);
    expect((await win.fetch("/api/reject")).status).toBe(404);
    expect(error).toHaveBeenCalled();
    error.mockRestore();
  });

  it("answers 404 JSON with portfolioMock.notFound()", async () => {
    win.portfolioMock.handle("GET", "/api/me", () => win.portfolioMock.notFound());
    const res = await win.fetch("/api/me");
    expect(res.status).toBe(404);
    expect(res.headers.get("Content-Type")).toBe("application/json");
    expect(await res.json()).toEqual({ error: "not found" });
  });

  it("answers 404 for unmatched local development origins without a network error", async () => {
    for (const url of ["http://localhost:8000/api/x", "http://127.0.0.1:3000/x", "http://[::1]:8000/x"]) {
      expect((await win.fetch(url, { method: "POST" })).status).toBe(404);
    }
    expect(realFetch).not.toHaveBeenCalled();
  });

  it("passes a malformed percent-escape through without throwing", async () => {
    win.portfolioMock.handle("GET", "/api/items/:id", (req) => ({ id: req.params.id }));
    expect(await (await win.fetch("/api/items/100%")).json()).toEqual({ id: "100%" });
  });

  it("uses the first matching handler", async () => {
    win.portfolioMock.handle("GET", "/api/items/new", () => ({ v: "new" }));
    win.portfolioMock.handle("GET", "/api/items/:id", () => ({ v: "id" }));
    expect(await (await win.fetch("/api/items/new")).json()).toEqual({ v: "new" });
  });
});
