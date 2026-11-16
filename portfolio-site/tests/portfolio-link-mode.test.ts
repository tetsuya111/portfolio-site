import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { appBackendModes, readAppBackendModes } from "../src/lib/apps-manifest";

const app = (over: Record<string, unknown> = {}) => ({ slug: "a", outputDir: "dist", buildArgs: [], ...over });

describe("appBackendModes", () => {
  it("maps mock: true to mock and others to api", () => {
    const modes = appBackendModes({ apps: [app({ mock: true }), app({ slug: "b", mock: false }), app({ slug: "c" })] });
    expect([...modes]).toEqual([
      ["a", "mock"],
      ["b", "api"],
      ["c", "api"],
    ]);
  });

  it("returns an empty map for invalid data (the page build must not stop)", () => {
    expect(appBackendModes(null).size).toBe(0);
    expect(appBackendModes({ apps: [app({ slug: "Bad!" })] }).size).toBe(0);
  });
});

describe("readAppBackendModes", () => {
  it("reads apps.json and tolerates a missing or broken file", () => {
    const dir = mkdtempSync(join(tmpdir(), "modes-"));
    try {
      const file = join(dir, "apps.json");
      expect(readAppBackendModes(file).size).toBe(0);
      writeFileSync(file, "{");
      expect(readAppBackendModes(file).size).toBe(0);
      writeFileSync(file, JSON.stringify({ apps: [app({ mock: true })] }));
      expect(readAppBackendModes(file).get("a")).toBe("mock");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
