import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { parsePortfolioArgs, runNewPortfolio } from "../src/lib/portfolio-cli";
import { ContentValidationError } from "../src/lib/errors";

describe("parsePortfolioArgs", () => {
  it("parses and trims tags", () => {
    expect(
      parsePortfolioArgs(["--slug", "my-app", "--title", "My App", "--tags", "Astro, AWS ,"]),
    ).toEqual({ slug: "my-app", title: "My App", tags: ["Astro", "AWS"] });
  });

  it("accepts url and no tags", () => {
    expect(parsePortfolioArgs(["--slug", "a", "--title", "A", "--url", "https://x.example"])).toEqual(
      { slug: "a", title: "A", tags: [], url: "https://x.example" },
    );
  });

  it("requires --slug even for a Japanese title", () => {
    expect(() => parsePortfolioArgs(["--title", "日本語のタイトル"])).toThrow(/--slug/);
  });

  it.each([
    [["--slug", "a"]],
    [["--slug", "a", "--title", "A", "--url", "javascript:alert(1)"]],
    [["--slug", "Bad Slug", "--title", "A"]],
    [["--slug", "a", "--title", "A", "--unknown", "x"]],
    [["--slug", "a", "--title", "   "]],
  ])("rejects %j", (argv) => {
    expect(() => parsePortfolioArgs(argv)).toThrow(ContentValidationError);
  });
});

describe("runNewPortfolio", () => {
  let root: string;
  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), "portfolio-cli-"));
  });
  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it("creates the file and reports its path", async () => {
    const r = await runNewPortfolio(["--slug", "a", "--title", "A", "--tags", "x"], root, new Date(2026, 10, 13));
    expect(r.exitCode).toBe(0);
    expect(r.message).toContain(join(root, "portfolios", "a.md"));
    expect(await readFile(join(root, "portfolios", "a.md"), "utf8")).toContain("date: 2026-11-13");
  });

  it("fails with exit code 1 on duplicate slug", async () => {
    await runNewPortfolio(["--slug", "a", "--title", "A"], root);
    const r = await runNewPortfolio(["--slug", "a", "--title", "B"], root);
    expect(r.exitCode).toBe(1);
    expect(r.message).toMatch(/既に/);
  });

  it("fails with exit code 1 on invalid arguments", async () => {
    const r = await runNewPortfolio(["--title", "A"], root);
    expect(r.exitCode).toBe(1);
    expect(r.message).toContain("--slug");
  });
});
