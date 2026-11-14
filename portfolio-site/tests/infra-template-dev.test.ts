import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { loadCfnTemplate } from "./helpers/cfn-yaml";

// dev 環境（S3 へのアップロードのみ）のテンプレート。本番の template.yaml とは別スタックで作る
const t = loadCfnTemplate(join(import.meta.dirname, "..", "infra", "template.dev.yaml"));
const R = t.Resources;
const ofType = (type: string) => Object.values(R).filter((r) => (r as { Type: string }).Type === type) as any[];
const one = (type: string) => {
  const list = ofType(type);
  expect(list).toHaveLength(1);
  return list[0];
};

describe("infra/template.dev.yaml", () => {
  it("declares the parameters (deploy branch defaults to dev-release)", () => {
    expect(Object.keys(t.Parameters).sort()).toEqual(["DeployBranch", "DeployPath", "GitHubRepoUrl"]);
    expect(t.Parameters.DeployBranch.Default).toBe("dev-release");
    expect(t.Parameters.DeployPath.Default).toBe("");
    expect(t.Conditions.HasDeployPath).toEqual({ "Fn::Not": [{ "Fn::Equals": [{ Ref: "DeployPath" }, ""] }] });
  });

  it("does not accept an empty deploy branch", () => {
    const re = new RegExp(t.Parameters.DeployBranch.AllowedPattern);
    expect(re.test("dev-release")).toBe(true);
    expect(re.test("")).toBe(false);
  });

  it("accepts only relative S3 prefixes without empty or dot segments as DeployPath", () => {
    const re = new RegExp(t.Parameters.DeployPath.AllowedPattern);
    for (const ok of ["", "preview", "a/b-c", "v1.2/site_x"]) expect(re.test(ok), ok).toBe(true);
    for (const ng of ["../x", "/x", "x/", "a/../b", "a//b", ".", "a b"]) expect(re.test(ng), ng).toBe(false);
  });

  it("keeps the bucket private, encrypted and HTTPS-only", () => {
    const b = one("AWS::S3::Bucket").Properties;
    expect(b.PublicAccessBlockConfiguration).toEqual({
      BlockPublicAcls: true,
      BlockPublicPolicy: true,
      IgnorePublicAcls: true,
      RestrictPublicBuckets: true,
    });
    expect(b.BucketEncryption).toBeDefined();
    expect(b.WebsiteConfiguration).toBeUndefined();
    const stmts = one("AWS::S3::BucketPolicy").Properties.PolicyDocument.Statement;
    expect(stmts.every((s: any) => s.Effect === "Deny")).toBe(true);
    expect(JSON.stringify(stmts)).toContain("aws:SecureTransport");
  });

  it("has no CloudFront, Route 53 or certificate resources", () => {
    const types = Object.values(R).map((r: any) => r.Type);
    expect(types.some((ty) => /CloudFront|Route53|CertificateManager/.test(ty))).toBe(false);
  });

  it("deploys with buildspec.dev.yml only on push to the deploy branch under portfolio-site/", () => {
    const p = one("AWS::CodeBuild::Project").Properties;
    expect(p.Source.BuildSpec).toBe("portfolio-site/buildspec.dev.yml");
    expect(p.ConcurrentBuildLimit).toBe(1);
    const groups = p.Triggers.FilterGroups;
    expect(groups).toHaveLength(1);
    const f = Object.fromEntries(groups[0].map((x: any) => [x.Type, x.Pattern]));
    expect(f.EVENT).toBe("PUSH");
    expect(f.HEAD_REF).toEqual({ "Fn::Sub": "^refs/heads/${DeployBranch}$" });
    expect(f.FILE_PATH).toBe("^portfolio-site/");
  });

  it("passes the bucket, path and branch as environment variables", () => {
    const vars = one("AWS::CodeBuild::Project").Properties.Environment.EnvironmentVariables;
    expect(Object.fromEntries(vars.map((v: any) => [v.Name, v.Value]))).toEqual({
      SITE_BUCKET: { Ref: "DevSiteBucket" },
      DEPLOY_PATH: { Ref: "DeployPath" },
      DEPLOY_BRANCH: { Ref: "DeployBranch" },
    });
  });

  it("limits the build role to logs and the dev bucket (prefix when DeployPath is set)", () => {
    const role = one("AWS::IAM::Role").Properties;
    const trust = JSON.stringify(role.AssumeRolePolicyDocument);
    expect(trust).toContain("aws:SourceAccount");
    expect(trust).toContain("${AWS::StackName}-deploy");
    const stmts = role.Policies.flatMap((p: any) => p.PolicyDocument.Statement);
    const actions = stmts.flatMap((s: any) => [s.Action].flat());
    for (const a of actions) expect(a).not.toContain("*");
    expect(actions.some((a: string) => a.startsWith("cloudfront:"))).toBe(false);
    const objects = stmts.find((s: any) => [s.Action].flat().includes("s3:PutObject"));
    expect(objects.Resource).toEqual({
      "Fn::If": ["HasDeployPath", { "Fn::Sub": "${DevSiteBucket.Arn}/${DeployPath}/*" }, { "Fn::Sub": "${DevSiteBucket.Arn}/*" }],
    });
  });
});
