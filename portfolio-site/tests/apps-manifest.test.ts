import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { type AppEntry, buildApps, validateManifest } from "../src/lib/apps-manifest";

const app = (over: Record<string, unknown> = {}) => ({ slug: "my-app", outputDir: "dist", buildArgs: ["--base=/apps/my-app/"], ...over });
const entry = (over: Record<string, unknown> = {}) => ({ ...app(), mock: false, ...over }) as AppEntry;

describe("validateManifest", () => {
  it("returns the apps of a valid manifest", () => {
    expect(validateManifest({ apps: [app(), app({ slug: "b", outputDir: "out", buildArgs: [], mock: true })] })).toEqual([
      { ...app(), mock: false },
      { slug: "b", outputDir: "out", buildArgs: [], mock: true },
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
    ["app root outputDir ./", { apps: [app({ outputDir: "./" })] }],
    ["app root outputDir dist/..", { apps: [app({ outputDir: "dist/.." })] }],
    ["app root outputDir ./.", { apps: [app({ outputDir: "./." })] }],
    ["shell metachar arg", { apps: [app({ buildArgs: ["--base=/x/;rm -rf /"] })] }],
    ["non-string arg", { apps: [app({ buildArgs: [1] })] }],
    ["non-boolean mock", { apps: [app({ mock: "true" })] }],
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
    buildApps([entry()], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run });
    const cwd = join(root, "apps", "my-app");
    expect(calls).toEqual([
      ["npm", "ci", "--ignore-scripts", cwd],
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
    buildApps([entry({ outputDir: "out", buildArgs: [] })], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run });
    expect(calls).toEqual([["ci", "--ignore-scripts"], ["run", "build"]]);
  });

  it("refuses to build without a lockfile (versions must be pinned)", () => {
    rmSync(join(root, "apps", "my-app", "package-lock.json"));
    const calls: string[][] = [];
    expect(() =>
      buildApps([entry()], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run: (_c, a) => (calls.push(a), 0) }),
    ).toThrow(/package-lock\.json/);
    expect(calls).toEqual([]);
  });

  it("throws when a command fails", () => {
    expect(() =>
      buildApps([entry()], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run: () => 1 }),
    ).toThrow(/my-app/);
  });

  it("throws when the app directory or the output is missing", () => {
    expect(() =>
      buildApps([entry({ slug: "nope" })], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run: () => 0 }),
    ).toThrow(/nope/);
    expect(() =>
      buildApps([entry()], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run: () => 0 }),
    ).toThrow(/dist/);
    expect(existsSync(join(root, "dist", "apps", "my-app"))).toBe(false);
  });

  describe("mock", () => {
    const tags =
      '<script src="/apps/my-app/__mock__/runtime.js" data-base="/apps/my-app"></script>' +
      '<script src="/apps/my-app/__mock__/handlers.js"></script>';
    const runtime = () => join(root, "runtime.js");
    const html: Record<string, string> = {
      "index.html": '<!doctype html><html><head><meta charset="utf-8"></head><body></body></html>',
      "sub/page.html": '<!DOCTYPE html><HTML><HEAD lang="ja"><title>x</title></HEAD></HTML>',
      "nohead.html": "<!doctype html><p>x</p>",
      "bare.html": "<p>x</p>",
      "__mock__s/index.html": "<html><head></head></html>",
    };
    const build = (run = (_c: string, args: string[], cwd: string) => {
      if (args[0] === "run") {
        for (const [name, text] of Object.entries(html)) {
          mkdirSync(join(cwd, "dist", name, ".."), { recursive: true });
          writeFileSync(join(cwd, "dist", name), text);
        }
        writeFileSync(join(cwd, "dist", "app.js"), "<head>");
      }
      return 0;
    }) => buildApps([entry({ mock: true })], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run, mockRuntime: runtime() });
    const out = (name: string) => readFileSync(join(root, "dist", "apps", "my-app", name), "utf8");

    beforeEach(() => {
      writeFileSync(runtime(), "// runtime");
      mkdirSync(join(root, "apps", "my-app", "mock"), { recursive: true });
      writeFileSync(join(root, "apps", "my-app", "mock", "handlers.js"), "// handlers");
    });

    it("copies the runtime and handlers into __mock__", () => {
      build();
      expect(out("__mock__/runtime.js")).toBe("// runtime");
      expect(out("__mock__/handlers.js")).toBe("// handlers");
    });

    it("injects the scripts right after <head> of every html file", () => {
      build();
      expect(out("index.html")).toBe(`<!doctype html><html><head>${tags}<meta charset="utf-8"></head><body></body></html>`);
      expect(out("sub/page.html")).toBe(`<!DOCTYPE html><HTML><HEAD lang="ja">${tags}<title>x</title></HEAD></HTML>`);
      expect(out("nohead.html")).toBe(`<!doctype html>${tags}<p>x</p>`);
      expect(out("bare.html")).toBe("<p>x</p>");
      expect(out("__mock__s/index.html")).toBe(`<html><head>${tags}</head></html>`);
      expect(out("app.js")).toBe("<head>");
    });

    it("does not inject when mock is false", () => {
      buildApps([entry()], {
        appsDir: join(root, "apps"),
        distDir: join(root, "dist"),
        mockRuntime: runtime(),
        run: (_c, args, cwd) => {
          if (args[0] === "run") {
            mkdirSync(join(cwd, "dist"), { recursive: true });
            writeFileSync(join(cwd, "dist", "index.html"), html["index.html"]);
          }
          return 0;
        },
      });
      expect(out("index.html")).toBe(html["index.html"]);
      expect(existsSync(join(root, "dist", "apps", "my-app", "__mock__"))).toBe(false);
    });

    it("fails before building when mock/handlers.js is missing", () => {
      rmSync(join(root, "apps", "my-app", "mock"), { recursive: true });
      const calls: string[][] = [];
      expect(() => build((_c, a) => (calls.push(a), 0))).toThrow(/mock\/handlers\.js/);
      expect(calls).toEqual([]);
    });
  });
});
