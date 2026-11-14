import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { loadCfnTemplate } from "./helpers/cfn-yaml";

const root = join(import.meta.dirname, "..");
const template = loadCfnTemplate(join(root, "infra", "template.yaml"));
// aws cloudformation deploy --parameter-overrides file://infra/parameters.json で読む形式
// （CodePipeline のテンプレート設定ファイルと同じ { "Parameters": { 名前: 値 } }）
const example: any = JSON.parse(readFileSync(join(root, "infra", "parameters.example.json"), "utf8"));

describe("infra/parameters.example.json", () => {
  it('is a { "Parameters": { name: string } } object', () => {
    expect(Object.keys(example)).toEqual(["Parameters"]);
    for (const value of Object.values(example.Parameters)) expect(typeof value).toBe("string");
  });

  it("sets every template parameter exactly once", () => {
    expect(Object.keys(example.Parameters).sort()).toEqual(Object.keys(template.Parameters).sort());
  });

  it("uses the template defaults for parameters that have one", () => {
    for (const [name, p] of Object.entries<any>(template.Parameters)) {
      if (p.Default !== undefined) expect(example.Parameters[name]).toBe(String(p.Default));
    }
  });

  it("keeps the real parameter file out of git (it holds the e-mail address and zone id)", () => {
    const ignore = readFileSync(join(root, ".gitignore"), "utf8").split(/\r?\n/);
    expect(ignore).toContain("infra/parameters.json");
  });
});
