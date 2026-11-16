import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch, getToken, login, setToken, setUnauthorizedHandler } from "./api";

function mockFetch(status: number, body?: unknown) {
  const fn = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  setUnauthorizedHandler(null);
});

describe("apiFetch", () => {
  it("attaches bearer token", async () => {
    setToken("abc");
    const fetchMock = mockFetch(200, { ok: true });
    await apiFetch("/users/me");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/users/me");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer abc");
  });

  it("sends JSON body with content type", async () => {
    const fetchMock = mockFetch(201, { id: 1 });
    await apiFetch("/products", { method: "POST", json: { sku: "A" } });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.body).toBe('{"sku":"A"}');
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("returns undefined for 204", async () => {
    mockFetch(204);
    await expect(apiFetch("/products/1", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("throws ApiError with detail", async () => {
    mockFetch(409, { detail: "在庫が不足しています" });
    await expect(apiFetch("/inventory/out")).rejects.toMatchObject({
      status: 409,
      message: "在庫が不足しています",
    });
  });

  it("joins validation error messages", async () => {
    mockFetch(422, { detail: [{ msg: "field required" }, { msg: "too long" }] });
    const error = (await apiFetch("/products").catch((e) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toContain("field required");
    expect(error.message).toContain("too long");
  });

  it("throws ApiError when the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(apiFetch("/health")).rejects.toMatchObject({ status: 0 });
  });

  it("calls the unauthorized handler on 401", async () => {
    setToken("expired");
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    mockFetch(401, { detail: "認証が必要です" });
    await expect(apiFetch("/users/me")).rejects.toBeInstanceOf(ApiError);
    expect(handler).toHaveBeenCalledOnce();
  });
});

describe("login", () => {
  it("posts form-encoded body and stores nothing by itself", async () => {
    const fetchMock = mockFetch(200, { access_token: "t", token_type: "bearer", expires_in: 3600 });
    const token = await login("alice", "p@ss word");
    expect(token.access_token).toBe("t");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/auth/login");
    expect(init.body.toString()).toBe("username=alice&password=p%40ss+word");
    expect(getToken()).toBeNull();
  });

  it("does not call the unauthorized handler for a failed login", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    mockFetch(401, { detail: "ユーザー名またはパスワードが正しくありません。" });
    await expect(login("alice", "bad")).rejects.toMatchObject({ status: 401 });
    expect(handler).not.toHaveBeenCalled();
  });
});
