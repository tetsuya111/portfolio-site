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

  it("deploys only for a successful push to the deploy branch (any branch when DEPLOY_BRANCH is empty)", () => {
    const post = commands("post_build").join("\n");
    const guard = post.indexOf("CODEBUILD_WEBHOOK_EVENT");
    expect(guard).toBeGreaterThanOrEqual(0);
    expect(post).toContain("CODEBUILD_BUILD_SUCCEEDING");
    expect(post).toContain('refs/heads/$DEPLOY_BRANCH');
    expect(post).toContain('-z "$DEPLOY_BRANCH"');
    // タグなどブランチ以外の push ではデプロイしない
    expect(post).toContain("refs/heads/*");
    expect(post.indexOf("aws s3 sync")).toBeGreaterThan(guard);
    expect(post.indexOf("create-invalidation")).toBeGreaterThan(guard);
    expect(post).toContain("--delete");
  });

  it("syncs to the bucket root or DEPLOY_PATH without a double slash", () => {
    const post = commands("post_build").join("\n");
    expect(post).toContain('aws s3 sync dist "s3://$SITE_BUCKET/${DEPLOY_PATH:+$DEPLOY_PATH/}" --delete');
  });

  it("invalidates CloudFront only when DISTRIBUTION_ID is set (EnableCloudFront=false leaves it empty)", () => {
    const post = commands("post_build").join("\n");
    expect(post.indexOf('-n "$DISTRIBUTION_ID"')).toBeGreaterThan(post.indexOf("aws s3 sync"));
    // 無効化は DISTRIBUTION_ID の if ブロックの中だけで行う
    expect(post).toMatch(/if \[ -n "\$DISTRIBUTION_ID" \]; then\s*\n\s*aws cloudfront create-invalidation [^\n]*\n\s*fi\n/);
    expect(post.match(/create-invalidation/g)).toHaveLength(1);
  });

  it("restores the auto-generated IT articles from S3 before building (only when IT_ARTICLES_BUCKET is set)", () => {
    const pre = commands("pre_build").join("\n");
    expect(pre).toMatch(
      /if \[ -n "\$IT_ARTICLES_BUCKET" \]; then\s*\n\s*aws s3 sync "s3:\/\/\$IT_ARTICLES_BUCKET\/it-articles\/" src\/content\/it-articles\//,
    );
    // 取り込みでローカルのファイルを消さない・md 以外を持ち込まない
    expect(pre).not.toContain("--delete");
    expect(pre).toContain('--exclude "*" --include "*.md"');
  });

  it("does not run aws commands outside pre_build and post_build", () => {
    for (const phase of ["install", "build"]) {
      expect(commands(phase).join("\n")).not.toMatch(/\baws\b/);
    }
  });
});

describe("buildspec.it-articles.yml", () => {
  const itSpec = parse(readFileSync(join(import.meta.dirname, "..", "buildspec.it-articles.yml"), "utf8"));
  const c = (phase: string): string[] => itSpec.phases[phase]?.commands ?? [];

  it("uses Node.js 22 and Python 3.12 and installs without dependency scripts", () => {
    expect(String(itSpec.phases.install["runtime-versions"].nodejs)).toBe("22");
    expect(String(itSpec.phases.install["runtime-versions"].python)).toBe("3.12");
    const installs = c("install").filter((l) => l.includes("npm ci"));
    expect(installs).toHaveLength(1);
    expect(installs[0]).toContain("--ignore-scripts");
  });

  it("pins boto3", () => {
    expect(c("install").join("\n")).toMatch(/pip install [^\n]*"boto3==\d+\.\d+\.\d+"/);
  });

  it("restores past articles, generates new ones and then builds the site", () => {
    expect(c("pre_build").join("\n")).toContain('aws s3 sync "s3://$IT_ARTICLES_BUCKET/it-articles/" src/content/it-articles/');
    const build = c("build");
    const gen = build.findIndex((l) => l.includes("generate_it_articles.py --out-dir src/content/it-articles"));
    const site = build.findIndex((l) => l.includes("npm run test:build"));
    expect(gen).toBeGreaterThanOrEqual(0);
    expect(site).toBeGreaterThan(gen);
  });

  it("saves the articles and deploys the diff only after a successful build", () => {
    const post = c("post_build").join("\n");
    const guard = post.indexOf('"$CODEBUILD_BUILD_SUCCEEDING" = "1"');
    const save = post.indexOf('aws s3 sync src/content/it-articles/ "s3://$IT_ARTICLES_BUCKET/it-articles/"');
    const deploy = post.indexOf("deploy_diff.py");
    expect(guard).toBeGreaterThanOrEqual(0);
    expect(save).toBeGreaterThan(guard);
    expect(deploy).toBeGreaterThan(save);
    expect(post).toContain('PREFIX="$DEPLOY_PATH"');
    expect(post).toContain('BUCKET="$SITE_BUCKET"');
  });

  it("never deletes from the buckets (apps/ is not built here)", () => {
    const all = Object.keys(itSpec.phases).flatMap(c).join("\n");
    expect(all).not.toContain("--delete");
    expect(all).not.toContain("DELETE_REMOVED");
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
