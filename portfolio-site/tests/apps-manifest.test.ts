import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { buildApps, validateManifest } from "../src/lib/apps-manifest";

const app = (over: Record<string, unknown> = {}) => ({
  slug: "my-app",
  outputDir: "dist",
  buildArgs: ["--base=/apps/my-app/"],
  env: {},
  ...over,
});

describe("validateManifest", () => {
  it("returns the apps of a valid manifest", () => {
    expect(validateManifest({ apps: [app(), app({ slug: "b", outputDir: "out", buildArgs: [] })] })).toEqual([
      app(),
      { slug: "b", outputDir: "out", buildArgs: [], env: {} },
    ]);
  });

  it("treats a missing env as empty and keeps a valid env", () => {
    const noEnv: Record<string, unknown> = app();
    delete noEnv.env;
    expect(validateManifest({ apps: [noEnv] })[0].env).toEqual({});
    const env = { VITE_API_URL: "https://api.example.com", NEXT_PUBLIC_BACKEND_URL: "https://x.example.com:8443/v1/" };
    expect(validateManifest({ apps: [app({ env })] })[0].env).toEqual(env);
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
    ["env not object", { apps: [app({ env: ["VITE_API_URL"] })] }],
    ["env null", { apps: [app({ env: null })] }],
    ["env name without public prefix", { apps: [app({ env: { NODE_OPTIONS: "https://a.example.com" } })] }],
    ["env name PATH", { apps: [app({ env: { PATH: "https://a.example.com" } })] }],
    ["env name lowercase", { apps: [app({ env: { VITE_api: "https://a.example.com" } })] }],
    ["env value http", { apps: [app({ env: { VITE_API_URL: "http://a.example.com" } })] }],
    ["env value with query", { apps: [app({ env: { VITE_API_URL: "https://a.example.com/?a=1" } })] }],
    ["env value with quote", { apps: [app({ env: { VITE_API_URL: 'https://a.example.com/"' } })] }],
    ["env value not string", { apps: [app({ env: { VITE_API_URL: 1 } })] }],
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
      ["npm", "ci", "--ignore-scripts", cwd],
      ["npm", "run", "build", "--", "--base=/apps/my-app/", cwd],
    ]);
    expect(readFileSync(join(root, "dist", "apps", "my-app", "index.html"), "utf8")).toBe("hi");
  });

  it("passes env to both npm ci and npm run build", () => {
    const envs: Record<string, string>[] = [];
    const run = (_cmd: string, args: string[], cwd: string, env: Record<string, string>) => {
      envs.push(env);
      if (args[0] === "run") mkdirSync(join(cwd, "dist"), { recursive: true });
      return 0;
    };
    const env = { VITE_API_URL: "https://api.example.com" };
    buildApps([app({ env })], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run });
    expect(envs).toEqual([env, env]);
  });

  it("omits -- when there are no build args", () => {
    const calls: string[][] = [];
    const run = (cmd: string, args: string[], cwd: string) => {
      calls.push(args);
      mkdirSync(join(cwd, "out"), { recursive: true });
      return 0;
    };
    buildApps([app({ outputDir: "out", buildArgs: [] })], { appsDir: join(root, "apps"), distDir: join(root, "dist"), run });
    expect(calls).toEqual([["ci", "--ignore-scripts"], ["run", "build"]]);
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
