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

  it("does not run dependency install scripts with deploy credentials", () => {
    const installs = commands("install").filter((l) => l.includes("npm ci"));
    expect(installs.length).toBeGreaterThan(0);
    for (const l of installs) expect(l).toContain("--ignore-scripts");
  });

  it("runs test, lint and build with output checks in order", () => {
    const build = commands("build");
    const idx = ["npm test", "npm run lint", "npm run test:build"].map((c) => build.findIndex((l) => l.includes(c)));
    expect(idx.every((i) => i >= 0)).toBe(true);
    expect([...idx].sort((a, b) => a - b)).toEqual(idx);
  });

  it("builds the portfolio apps into dist after the astro build", () => {
    const build = commands("build");
    const astro = build.findIndex((l) => l.includes("npm run test:build"));
    const apps = build.findIndex((l) => l.includes("npm run build:apps"));
    expect(apps).toBeGreaterThan(astro);
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

describe("buildspec.test.yml", () => {
  const testSpec = parse(readFileSync(join(import.meta.dirname, "..", "buildspec.test.yml"), "utf8"));
  const testCommands = (phase: string): string[] => testSpec.phases[phase]?.commands ?? [];

  it("uses Node.js 22 and installs from the lockfile", () => {
    expect(String(testSpec.phases.install["runtime-versions"].nodejs)).toBe("22");
    expect(testCommands("install").join("\n")).toContain("npm ci");
  });

  it("runs the same checks as the deploy buildspec", () => {
    expect(testCommands("build")).toEqual(commands("build"));
  });

  it("never deploys", () => {
    expect(testSpec.phases.post_build).toBeUndefined();
    const all = Object.keys(testSpec.phases).flatMap(testCommands).join("\n");
    expect(all).not.toMatch(/\baws\b/);
    expect(all).not.toMatch(/SITE_BUCKET|DISTRIBUTION_ID/);
  });
});
