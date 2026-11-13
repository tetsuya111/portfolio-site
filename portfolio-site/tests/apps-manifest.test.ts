import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { buildApps, validateManifest } from "../src/lib/apps-manifest";

const app = (over: Record<string, unknown> = {}) => ({ slug: "my-app", outputDir: "dist", buildArgs: ["--base=/apps/my-app/"], ...over });

describe("validateManifest", () => {
  it("returns the apps of a valid manifest", () => {
    expect(validateManifest({ apps: [app(), app({ slug: "b", outputDir: "out", buildArgs: [] })] })).toEqual([
      app(),
      { slug: "b", outputDir: "out", buildArgs: [] },
    ]);
  });

  it.each([
    ["apps not array", { apps: {} }],
    ["not object", null],
    ["bad slug", { apps: [app({ slug: "My_App" })] }],
    ["duplicate slug", { apps: [app(), app()] }],
    ["parent outputDir", { apps: [app({ outputDir: "../x" })] }],
    ["nested parent outputDir", { apps: [app({ outputDir: "dist/../../x" })] }],
    ["absolute outputDir", { apps: [app({ outputDir: "/etc" })] }],
    ["windows absolute outputDir", { apps: [app({ outputDir: "C:\\x" })] }],
    ["empty outputDir", { apps: [app({ outputDir: "" })] }],
    ["shell metachar arg", { apps: [app({ buildArgs: ["--base=/x/;rm -rf /"] })] }],
    ["non-string arg", { apps: [app({ buildArgs: [1] })] }],
  ])("rejects %s", (_name, data) => {
    expect(() => validateManifest(data)).toThrow();
  });
});

describe("buildApps", () => {
  let root: string;
  beforeEach(() => {
    root = mkdtempSync(join(tmpdir(), "apps-"));
    mkdirSync(join(root, "apps", "my-app"), { recursive: true });
    writeFileSync(join(root, "apps", "my-app", "package.json"), "{}");
    writeFileSync(join(root, "apps", "my-app", "package-lock.json"), "{}");
  });
  afterEach(() => rmSync(root, { recursive: true, force: true }));

  it("installs, builds and copies output to dist/apps/<slug>", () => {
    const calls: string[][] = [];
    const run = (cmd: string, args: string[], cwd: string) => {
      calls.push([cmd, ...args, cwd]);
      if (args[0] === "run") {
        mkdirSync(join(cwd, "dist"), { recursive: true });
        writeFileSync(join(cwd, "dist", "index.html"), "hi");
      }
      return 0;
    };
    buildApps([app()], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run });
    const cwd = join(root, "apps", "my-app");
    expect(calls).toEqual([
      ["npm", "ci", cwd],
      ["npm", "run", "build", "--", "--base=/apps/my-app/", cwd],
    ]);
    expect(readFileSync(join(root, "dist", "apps", "my-app", "index.html"), "utf8")).toBe("hi");
  });

  it("omits -- when there are no build args", () => {
    const calls: string[][] = [];
    const run = (cmd: string, args: string[], cwd: string) => {
      calls.push(args);
      mkdirSync(join(cwd, "out"), { recursive: true });
      return 0;
    };
    buildApps([app({ outputDir: "out", buildArgs: [] })], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run });
    expect(calls).toEqual([["ci"], ["run", "build"]]);
  });

  it("refuses to build without a lockfile (versions must be pinned)", () => {
    rmSync(join(root, "apps", "my-app", "package-lock.json"));
    const calls: string[][] = [];
    expect(() =>
      buildApps([app()], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run: (_c, a) => (calls.push(a), 0) }),
    ).toThrow(/package-lock\.json/);
    expect(calls).toEqual([]);
  });

  it("throws when a command fails", () => {
    expect(() =>
      buildApps([app()], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run: () => 1 }),
    ).toThrow(/my-app/);
  });

  it("throws when the app directory or the output is missing", () => {
    expect(() =>
      buildApps([app({ slug: "nope" })], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run: () => 0 }),
    ).toThrow(/nope/);
    expect(() =>
      buildApps([app()], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run: () => 0 }),
    ).toThrow(/dist/);
    expect(existsSync(join(root, "dist", "apps", "my-app"))).toBe(false);
  });
});
