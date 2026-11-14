import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { loadCfnTemplate } from "./helpers/cfn-yaml";

const root = join(import.meta.dirname, "..");
const template = loadCfnTemplate(join(root, "infra", "template.yaml"));
// aws cloudformation deploy --parameter-overrides file://infra/parameters.json で読む形式（"キー=値" の配列）
const example: unknown = JSON.parse(readFileSync(join(root, "infra", "parameters.example.json"), "utf8"));

describe("infra/parameters.example.json", () => {
  it('is a JSON array of "Key=Value" strings', () => {
    expect(Array.isArray(example)).toBe(true);
    for (const entry of example as unknown[]) {
      expect(typeof entry).toBe("string");
      expect(entry).toMatch(/^[A-Za-z0-9]+=.*$/);
    }
  });

  const keys = (example as string[]).map((e) => e.slice(0, e.indexOf("=")));

  it("sets every template parameter exactly once", () => {
    expect([...keys].sort()).toEqual(Object.keys(template.Parameters).sort());
  });

  it("uses the template defaults for parameters that have one", () => {
    const values = Object.fromEntries((example as string[]).map((e) => [e.slice(0, e.indexOf("=")), e.slice(e.indexOf("=") + 1)]));
    for (const [name, p] of Object.entries<any>(template.Parameters)) {
      if (p.Default !== undefined) expect(values[name]).toBe(String(p.Default));
    }
  });

  it("keeps the real parameter file out of git (it holds the e-mail address and zone id)", () => {
    const ignore = readFileSync(join(root, ".gitignore"), "utf8").split(/\r?\n/);
    expect(ignore).toContain("infra/parameters.json");
  });
});
