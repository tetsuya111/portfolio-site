import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { loadCfnTemplate } from "./helpers/cfn-yaml";

const t = loadCfnTemplate(join(import.meta.dirname, "..", "infra", "template.yaml"));
const R = t.Resources;
const ofType = (type: string) => Object.values(R).filter((r) => (r as { Type: string }).Type === type) as any[];
const one = (type: string) => {
  const list = ofType(type);
  expect(list).toHaveLength(1);
  return list[0];
};

describe("infra/template.yaml", () => {
  it("declares the parameters", () => {
    expect(Object.keys(t.Parameters).sort()).toEqual(["DeployBranch", "DomainName", "GitHubRepoUrl", "HostedZoneId"]);
    expect(t.Parameters.DeployBranch.Default).toBe("main");
  });

  it("requires us-east-1", () => {
    const assertions = Object.values(t.Rules).flatMap((r: any) => r.Assertions);
    expect(JSON.stringify(assertions)).toContain('"AWS::Region"');
    expect(JSON.stringify(assertions)).toContain('"us-east-1"');
  });

  it("keeps the bucket private and encrypted", () => {
    const b = one("AWS::S3::Bucket").Properties;
    expect(b.PublicAccessBlockConfiguration).toEqual({
      BlockPublicAcls: true,
      BlockPublicPolicy: true,
      IgnorePublicAcls: true,
      RestrictPublicBuckets: true,
    });
    expect(b.BucketEncryption).toBeDefined();
  });

  it("allows only CloudFront of this distribution to read the bucket", () => {
    const stmts = one("AWS::S3::BucketPolicy").Properties.PolicyDocument.Statement;
    const read = stmts.find((s: any) => s.Action === "s3:GetObject");
    expect(read.Principal).toEqual({ Service: "cloudfront.amazonaws.com" });
    expect(read.Condition.StringEquals["AWS:SourceArn"]).toBeDefined();
    expect(JSON.stringify(stmts)).toContain("aws:SecureTransport");
  });

  it("issues a DNS-validated certificate in the hosted zone", () => {
    const c = one("AWS::CertificateManager::Certificate").Properties;
    expect(c.ValidationMethod).toBe("DNS");
    expect(c.DomainValidationOptions[0].HostedZoneId).toEqual({ Ref: "HostedZoneId" });
  });

  it("serves over HTTPS only via OAC with a directory-index function", () => {
    one("AWS::CloudFront::OriginAccessControl");
    const fn = one("AWS::CloudFront::Function");
    expect(fn.Properties.FunctionCode).toContain("index.html");
    const d = one("AWS::CloudFront::Distribution").Properties.DistributionConfig;
    expect(d.Aliases).toEqual([{ Ref: "DomainName" }]);
    expect(d.DefaultCacheBehavior.ViewerProtocolPolicy).toBe("redirect-to-https");
    expect(d.ViewerCertificate.MinimumProtocolVersion).toBe("TLSv1.2_2021");
    expect(d.ViewerCertificate.SslSupportMethod).toBe("sni-only");
    expect(d.Origins[0].OriginAccessControlId).toBeDefined();
    expect(d.DefaultCacheBehavior.FunctionAssociations[0].EventType).toBe("viewer-request");
    expect(d.CustomErrorResponses.map((e: any) => e.ResponsePagePath)).toEqual(["/404.html", "/404.html"]);
  });

  it("points the domain at CloudFront for IPv4 and IPv6", () => {
    const records = ofType("AWS::Route53::RecordSet").map((r) => r.Properties);
    expect(records.map((r) => r.Type).sort()).toEqual(["A", "AAAA"]);
    for (const r of records) expect(r.AliasTarget.HostedZoneId).toBe("Z2FDTNDATAQYW2");
  });

  describe("CodeBuild", () => {
    const testProject = R.CodeBuildTestProject?.Properties;
    const deployProject = R.CodeBuildProject?.Properties;
    const eventOf = (g: any[]) => g.find((f) => f.Type === "EVENT").Pattern;
    const filePathOf = (g: any[]) => g.find((f) => f.Type === "FILE_PATH").Pattern;
    const actionsOf = (roleId: string): string[] =>
      R[roleId].Properties.Policies.flatMap((p: any) => p.PolicyDocument.Statement).flatMap((s: any) =>
        Array.isArray(s.Action) ? s.Action : [s.Action],
      );

    it("has a test project and a deploy project", () => {
      expect(ofType("AWS::CodeBuild::Project")).toHaveLength(2);
      for (const p of [testProject, deployProject]) {
        expect(p.Source.Type).toBe("GITHUB");
        expect(p.Environment.Image).toBe("aws/codebuild/amazonlinux-x86_64-standard:5.0");
      }
    });

    it("runs pull requests with the test buildspec only", () => {
      expect(testProject.Source.BuildSpec).toBe("portfolio-site/buildspec.test.yml");
      const groups = testProject.Triggers.FilterGroups;
      expect(groups).toHaveLength(1);
      expect(eventOf(groups[0])).toBe("PULL_REQUEST_CREATED,PULL_REQUEST_UPDATED,PULL_REQUEST_REOPENED");
      expect(filePathOf(groups[0])).toBe("^portfolio-site/");
      // デプロイ先の情報を渡さない
      expect(testProject.Environment.EnvironmentVariables ?? []).toEqual([]);
    });

    it("runs pushes to the deploy branch with the deploy buildspec", () => {
      expect(deployProject.Source.BuildSpec).toBe("portfolio-site/buildspec.yml");
      const groups = deployProject.Triggers.FilterGroups;
      expect(groups).toHaveLength(1);
      expect(eventOf(groups[0])).toBe("PUSH");
      expect(filePathOf(groups[0])).toBe("^portfolio-site/");
      expect(JSON.stringify(groups[0].find((f: any) => f.Type === "HEAD_REF").Pattern)).toContain("refs/heads/");
      const env = Object.fromEntries(deployProject.Environment.EnvironmentVariables.map((v: any) => [v.Name, v.Value]));
      expect(Object.keys(env).sort()).toEqual(["DEPLOY_BRANCH", "DISTRIBUTION_ID", "SITE_BUCKET"]);
    });

    it("uses separate roles so pull request builds cannot deploy", () => {
      expect(testProject.ServiceRole).toEqual({ "Fn::GetAtt": ["CodeBuildTestRole", "Arn"] });
      expect(deployProject.ServiceRole).toEqual({ "Fn::GetAtt": ["CodeBuildRole", "Arn"] });
      const testActions = actionsOf("CodeBuildTestRole");
      expect(testActions.sort()).toEqual(["logs:CreateLogStream", "logs:PutLogEvents"]);
      expect(actionsOf("CodeBuildRole")).toContain("cloudfront:CreateInvalidation");
    });

    it("grants no wildcard actions", () => {
      for (const roleId of ["CodeBuildTestRole", "CodeBuildRole"]) {
        for (const a of actionsOf(roleId)) expect(a).not.toContain("*");
      }
    });
  });

  it("outputs the site url, bucket and distribution id", () => {
    expect(Object.keys(t.Outputs).sort()).toEqual(["BucketName", "DistributionId", "SiteUrl"]);
  });
});
