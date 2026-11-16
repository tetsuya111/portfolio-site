import { mkdtempSync, rmSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { appBackendModes, readAppBackendModes } from "../src/lib/apps-manifest";

const app = (over: Record<string, unknown> = {}) => ({ slug: "a", outputDir: "dist", buildArgs: [], ...over });
const env = { VITE_API_URL: "https://api.portfolio.link/x" };

describe("appBackendModes", () => {
  it("maps mock: true to mock and apps with env to api", () => {
    const modes = appBackendModes({
      apps: [app({ mock: true, env }), app({ slug: "b", mock: false, env }), app({ slug: "c", env })],
    });
    expect([...modes]).toEqual([
      ["a", "mock"],
      ["b", "api"],
      ["c", "api"],
    ]);
  });

  it("leaves out apps without a backend (no mock, no env)", () => {
    expect(appBackendModes({ apps: [app({ mock: false }), app({ slug: "b" })] }).size).toBe(0);
  });

  it("returns an empty map for invalid data (the page build must not stop)", () => {
    expect(appBackendModes(null).size).toBe(0);
    expect(appBackendModes({ apps: [app({ slug: "Bad!" })] }).size).toBe(0);
  });
});

describe("readAppBackendModes", () => {
  it("reads apps.json until it changes and tolerates a missing or broken file", () => {
    const dir = mkdtempSync(join(tmpdir(), "modes-"));
    try {
      expect(readAppBackendModes(join(dir, "missing.json")).size).toBe(0);
      const broken = join(dir, "broken.json");
      writeFileSync(broken, "{");
      expect(readAppBackendModes(broken).size).toBe(0);
      const file = join(dir, "apps.json");
      writeFileSync(file, JSON.stringify({ apps: [app({ mock: true })] }));
      expect(readAppBackendModes(file).get("a")).toBe("mock");
      // ファイルが変わらなければ読み直さない（ボタンごとにファイルを読まない）
      expect(readAppBackendModes(file)).toBe(readAppBackendModes(file));
      // 変わったら読み直す（astro dev で apps.json を変えたとき）
      writeFileSync(file, JSON.stringify({ apps: [] }));
      utimesSync(file, new Date(), new Date(Date.now() + 60_000));
      expect(readAppBackendModes(file).size).toBe(0);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
