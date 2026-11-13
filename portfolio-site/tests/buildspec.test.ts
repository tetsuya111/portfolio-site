import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { parse } from "yaml";

const spec = parse(readFileSync(join(import.meta.dirname, "..", "buildspec.yml"), "utf8"));
const commands = (phase: string): string[] => spec.phases[phase].commands;

describe("buildspec.yml", () => {
  it("uses Node.js 22 and installs from the lockfile", () => {
    expect(String(spec.phases.install["runtime-versions"].nodejs)).toBe("22");
    expect(commands("install").join("\n")).toContain("npm ci");
  });

  it("runs test, lint and build in order", () => {
    const build = commands("build");
    const idx = ["npm test", "npm run lint", "npm run build"].map((c) => build.findIndex((l) => l.includes(c)));
    expect(idx.every((i) => i >= 0)).toBe(true);
    expect([...idx].sort((a, b) => a - b)).toEqual(idx);
  });

  it("deploys only for a successful push to the deploy branch", () => {
    const post = commands("post_build").join("\n");
    const guard = post.indexOf("CODEBUILD_WEBHOOK_EVENT");
    expect(guard).toBeGreaterThanOrEqual(0);
    expect(post).toContain("CODEBUILD_BUILD_SUCCEEDING");
    expect(post).toContain('refs/heads/$DEPLOY_BRANCH');
    expect(post.indexOf("aws s3 sync")).toBeGreaterThan(guard);
    expect(post.indexOf("create-invalidation")).toBeGreaterThan(guard);
    expect(post).toContain("--delete");
  });

  it("does not run aws commands outside post_build", () => {
    for (const phase of ["install", "build"]) {
      expect(commands(phase).join("\n")).not.toMatch(/\baws\b/);
    }
  });
});
