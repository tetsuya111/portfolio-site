import { mkdtemp, mkdir, readFile, readdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createArticle, createPortfolio, saveProfile } from "../src/lib/content-store";
import { ContentConflictError, ContentValidationError } from "../src/lib/errors";
import { parseMarkdown } from "../src/lib/markdown-file";

let base: string;
let root: string;

beforeEach(async () => {
  base = await mkdtemp(join(tmpdir(), "content-store-"));
  root = join(base, "content");
  await mkdir(root);
});

afterEach(async () => {
  await rm(base, { recursive: true, force: true });
});

const PROFILE = "---\nname: Taro\nrole: Engineer\n---\n経歴\n";
const ARTICLE = "---\ntitle: Hello\ndate: 2026-11-13\n---\n本文\n";

describe("saveProfile", () => {
  it("writes profile.md", async () => {
    await saveProfile(root, PROFILE);
    expect(await readFile(join(root, "profile", "profile.md"), "utf8")).toBe(PROFILE);
  });

  it("rejects missing name and keeps the existing file", async () => {
    await saveProfile(root, PROFILE);
    await expect(saveProfile(root, "---\nrole: x\n---\n")).rejects.toThrow(ContentValidationError);
    expect(await readFile(join(root, "profile", "profile.md"), "utf8")).toBe(PROFILE);
  });

  it("leaves no temporary files behind", async () => {
    await saveProfile(root, PROFILE);
    await saveProfile(root, PROFILE.replace("Taro", "Jiro"));
    expect(await readdir(join(root, "profile"))).toEqual(["profile.md"]);
  });
});

describe("createArticle", () => {
  it("creates articles/<slug>.md and returns its path", async () => {
    const path = await createArticle(root, "hello", ARTICLE);
    expect(path).toBe(join(root, "articles", "hello.md"));
    expect(await readFile(path, "utf8")).toBe(ARTICLE);
  });

  it("refuses to overwrite an existing article", async () => {
    await createArticle(root, "hello", ARTICLE);
    await expect(createArticle(root, "hello", ARTICLE.replace("本文", "別"))).rejects.toThrow(
      ContentConflictError,
    );
    expect(await readFile(join(root, "articles", "hello.md"), "utf8")).toBe(ARTICLE);
  });

  it("rejects a path-like slug without writing outside the root", async () => {
    await expect(createArticle(root, "../evil", ARTICLE)).rejects.toThrow(ContentValidationError);
    expect(await readdir(base)).toEqual(["content"]);
  });

  it("rejects an invalid date", async () => {
    await expect(
      createArticle(root, "bad", "---\ntitle: a\ndate: 2026-13-40\n---\n"),
    ).rejects.toThrow(ContentValidationError);
  });

  it("rejects an existing file even when created concurrently", async () => {
    await mkdir(join(root, "articles"));
    await writeFile(join(root, "articles", "x.md"), "keep");
    await expect(createArticle(root, "x", ARTICLE)).rejects.toThrow(ContentConflictError);
    expect(await readFile(join(root, "articles", "x.md"), "utf8")).toBe("keep");
  });
});

describe("createPortfolio", () => {
  it("writes frontmatter that parses back", async () => {
    const path = await createPortfolio(root, {
      slug: "my-app",
      title: "My App",
      tags: ["Astro", "AWS"],
      url: "https://example.com",
      date: "2026-11-13",
    });
    expect(path).toBe(join(root, "portfolios", "my-app.md"));
    const { data, body } = parseMarkdown(await readFile(path, "utf8"));
    expect(data).toEqual({
      title: "My App",
      tags: ["Astro", "AWS"],
      url: "https://example.com",
      date: "2026-11-13",
    });
    expect(body).toContain("## 概要");
  });

  it("omits url when not given", async () => {
    const path = await createPortfolio(root, { slug: "a", title: "A", tags: [] });
    expect(parseMarkdown(await readFile(path, "utf8")).data).not.toHaveProperty("url");
  });

  it("refuses duplicates", async () => {
    await createPortfolio(root, { slug: "a", title: "A", tags: [] });
    await expect(createPortfolio(root, { slug: "a", title: "B", tags: [] })).rejects.toThrow(
      ContentConflictError,
    );
  });

  it("rejects a javascript: url", async () => {
    await expect(
      createPortfolio(root, { slug: "a", title: "A", tags: [], url: "javascript:alert(1)" }),
    ).rejects.toThrow(ContentValidationError);
  });
});
