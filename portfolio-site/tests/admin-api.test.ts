import { mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { handleAdminRequest, type AdminRequest } from "../src/lib/admin-api";

let base: string;
let root: string;

beforeEach(async () => {
  base = await mkdtemp(join(tmpdir(), "admin-api-"));
  root = join(base, "content");
});

afterEach(async () => {
  await rm(base, { recursive: true, force: true });
});

const PROFILE = "---\nname: Taro\nrole: Engineer\n---\n経歴\n";
const ARTICLE = "---\ntitle: Hello\ndate: 2026-11-13\n---\n本文\n";

function req(overrides: Partial<AdminRequest> & { json?: unknown }): AdminRequest {
  const { json, ...rest } = overrides;
  return {
    method: "POST",
    path: "/__admin/api/articles",
    headers: {
      host: "localhost:4321",
      origin: "http://localhost:4321",
      "content-type": "application/json",
    },
    body: json === undefined ? "" : JSON.stringify(json),
    ...rest,
  };
}

const call = (r: AdminRequest) => handleAdminRequest(r, { contentRoot: root });

describe("handleAdminRequest", () => {
  it("saves the profile", async () => {
    const res = await call(req({ method: "PUT", path: "/__admin/api/profile", json: { markdown: PROFILE } }));
    expect(res.status).toBe(200);
    expect(await readFile(join(root, "profile", "profile.md"), "utf8")).toBe(PROFILE);
  });

  it("creates an article", async () => {
    const res = await call(req({ json: { slug: "hello", markdown: ARTICLE } }));
    expect(res.status).toBe(201);
    expect(await readFile(join(root, "articles", "hello.md"), "utf8")).toBe(ARTICLE);
  });

  it("accepts content-type with charset", async () => {
    const r = req({ json: { slug: "hello", markdown: ARTICLE } });
    r.headers["content-type"] = "application/json; charset=utf-8";
    expect((await call(r)).status).toBe(201);
  });

  it("rejects a missing Origin", async () => {
    const r = req({ json: { slug: "hello", markdown: ARTICLE } });
    delete r.headers.origin;
    expect((await call(r)).status).toBe(403);
  });

  it("rejects a cross-site Origin", async () => {
    const r = req({ json: { slug: "hello", markdown: ARTICLE } });
    r.headers.origin = "http://evil.example";
    expect((await call(r)).status).toBe(403);
    await expect(readdir(root)).rejects.toThrow();
  });

  it("rejects a non-JSON content type", async () => {
    const r = req({ json: { slug: "hello", markdown: ARTICLE } });
    r.headers["content-type"] = "text/plain";
    expect((await call(r)).status).toBe(415);
  });

  it("rejects broken JSON", async () => {
    expect((await call(req({ body: "{oops" }))).status).toBe(400);
  });

  it("rejects a body with wrong field types", async () => {
    expect((await call(req({ json: { slug: 1, markdown: ARTICLE } }))).status).toBe(400);
  });

  it("returns issues for invalid frontmatter", async () => {
    const res = await call(req({ json: { slug: "x", markdown: "---\ntitle: a\n---\n" } }));
    expect(res.status).toBe(400);
    expect(Array.isArray((res.json as { issues: unknown }).issues)).toBe(true);
  });

  it("rejects a path-like slug", async () => {
    const res = await call(req({ json: { slug: "../evil", markdown: ARTICLE } }));
    expect(res.status).toBe(400);
    expect(await readdir(base)).toEqual([]);
  });

  it("returns 409 for a duplicate slug", async () => {
    await call(req({ json: { slug: "hello", markdown: ARTICLE } }));
    expect((await call(req({ json: { slug: "hello", markdown: ARTICLE } }))).status).toBe(409);
  });

  it("has no portfolio endpoint", async () => {
    expect((await call(req({ path: "/__admin/api/portfolios", json: {} }))).status).toBe(404);
  });

  it("returns 405 for the wrong method", async () => {
    expect((await call(req({ method: "GET", path: "/__admin/api/profile" }))).status).toBe(405);
  });
});
