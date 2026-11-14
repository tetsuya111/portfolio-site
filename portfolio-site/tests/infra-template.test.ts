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
    expect(Object.keys(t.Parameters).sort()).toEqual([
      "BudgetAlertEmail",
      "DeployBranch",
      "DeployPath",
      "DomainName",
      "EnableCloudFront",
      "EnablePrTests",
      "EnableWaf",
      "GitHubActorAccountId",
      "GitHubRepoUrl",
      "HostedZoneId",
      "MonthlyBudgetUsd",
      "SiteBucketName",
    ]);
    // 未指定（空）なら任意のブランチへの push でデプロイする
    expect(t.Parameters.DeployBranch.Default).toBe("");
    expect(t.Conditions.HasDeployBranch).toEqual({ "Fn::Not": [{ "Fn::Equals": [{ Ref: "DeployBranch" }, ""] }] });
    expect(t.Parameters.GitHubActorAccountId.AllowedPattern).toBe("^[0-9]+$");
    expect(t.Parameters.EnableWaf.AllowedValues).toEqual(["true", "false"]);
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
    const read = stmts.find((s: any) => s["Fn::If"])["Fn::If"][1];
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
    // !If で出し分けるステートメントは両方の分岐を対象にする
    const statementsOf = (roleId: string): any[] =>
      R[roleId].Properties.Policies.flatMap((p: any) => p.PolicyDocument.Statement)
        .flatMap((s: any) => (s["Fn::If"] ? s["Fn::If"].slice(1) : [s]))
        .filter((s: any) => s.Ref !== "AWS::NoValue");
    const actionsOf = (roleId: string): string[] =>
      statementsOf(roleId).flatMap((s: any) => (Array.isArray(s.Action) ? s.Action : [s.Action]));

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
      // fork からの第三者の PR でビルドしない（指定した GitHub アカウントの PR だけ）
      expect(groups[0].find((f: any) => f.Type === "ACTOR_ACCOUNT_ID").Pattern).toEqual({
        "Fn::Sub": "^${GitHubActorAccountId}$",
      });
      // DeployBranch を指定したらそのブランチ向けの PR だけ、未指定なら任意のブランチ向け
      const baseRef = groups[0].find((f: any) => f.Type === "BASE_REF")?.Pattern;
      expect(baseRef).toEqual({
        "Fn::If": ["HasDeployBranch", { "Fn::Sub": "^refs/heads/${DeployBranch}$" }, "^refs/heads/"],
      });
      const [, withBranch, anyBranch] = baseRef["Fn::If"];
      const toMain = new RegExp(withBranch["Fn::Sub"].replace("${DeployBranch}", "main"));
      expect(toMain.test("refs/heads/main")).toBe(true);
      for (const ng of ["refs/heads/dev-main", "refs/heads/dev-release", "refs/heads/main-old"]) expect(toMain.test(ng), ng).toBe(false);
      expect(new RegExp(anyBranch).test("refs/heads/dev-release")).toBe(true);
      // デプロイ先の情報を渡さない
      expect(testProject.Environment.EnvironmentVariables ?? []).toEqual([]);
    });

    it("runs pushes to the deploy branch with the deploy buildspec", () => {
      expect(deployProject.Source.BuildSpec).toBe("portfolio-site/buildspec.yml");
      const groups = deployProject.Triggers.FilterGroups;
      expect(groups).toHaveLength(1);
      expect(eventOf(groups[0])).toBe("PUSH");
      expect(filePathOf(groups[0])).toBe("^portfolio-site/");
      // DeployBranch を指定したらそのブランチだけ、未指定なら任意のブランチ
      expect(groups[0].find((f: any) => f.Type === "HEAD_REF").Pattern).toEqual({
        "Fn::If": ["HasDeployBranch", { "Fn::Sub": "^refs/heads/${DeployBranch}$" }, "^refs/heads/"],
      });
      const env = Object.fromEntries(deployProject.Environment.EnvironmentVariables.map((v: any) => [v.Name, v.Value]));
      expect(Object.keys(env).sort()).toEqual(["DEPLOY_BRANCH", "DEPLOY_PATH", "DISTRIBUTION_ID", "SITE_BUCKET"]);
      expect(env.DEPLOY_PATH).toEqual({ Ref: "DeployPath" });
      // CloudFront を作らないときは空にし、buildspec はキャッシュ無効化を省略する
      expect(env.DISTRIBUTION_ID).toEqual({ "Fn::If": ["UseCloudFront", { Ref: "Distribution" }, ""] });
    });

    it("uses separate roles so pull request builds cannot deploy", () => {
      expect(testProject.ServiceRole).toEqual({ "Fn::GetAtt": ["CodeBuildTestRole", "Arn"] });
      expect(deployProject.ServiceRole).toEqual({ "Fn::GetAtt": ["CodeBuildRole", "Arn"] });
      const testActions = actionsOf("CodeBuildTestRole");
      expect(testActions.sort()).toEqual(["logs:CreateLogStream", "logs:PutLogEvents"]);
      expect(actionsOf("CodeBuildRole")).toContain("cloudfront:CreateInvalidation");
    });

    it("creates the pull request test project only when EnablePrTests is true", () => {
      expect(t.Parameters.EnablePrTests.Default).toBe("true");
      expect(t.Parameters.EnablePrTests.AllowedValues).toEqual(["true", "false"]);
      expect(t.Conditions.UsePrTests).toEqual({ "Fn::Equals": [{ Ref: "EnablePrTests" }, "true"] });
      for (const id of ["CodeBuildTestProject", "CodeBuildTestRole", "TestLogGroup"]) expect(R[id].Condition, id).toBe("UsePrTests");
      expect(R.CodeBuildProject.Condition).toBeUndefined();
    });

    it("limits the deploy role's S3 access to DeployPath when it is set", () => {
      const stmts = statementsOf("CodeBuildRole");
      const list = stmts.find((s: any) => s.Action === "s3:ListBucket");
      expect(list.Condition).toEqual({
        "Fn::If": ["HasDeployPath", { StringLike: { "s3:prefix": [{ "Fn::Sub": "${DeployPath}/*" }] } }, { Ref: "AWS::NoValue" }],
      });
      const objects = stmts.find((s: any) => [s.Action].flat().includes("s3:PutObject"));
      expect(objects.Resource).toEqual({
        "Fn::If": ["HasDeployPath", { "Fn::Sub": "${SiteBucket.Arn}/${DeployPath}/*" }, { "Fn::Sub": "${SiteBucket.Arn}/*" }],
      });
    });

    it("grants cache invalidation only when CloudFront is enabled", () => {
      const raw = R.CodeBuildRole.Properties.Policies.flatMap((p: any) => p.PolicyDocument.Statement);
      const inv = raw.find((s: any) => s["Fn::If"]?.[1]?.Sid === "InvalidateCache");
      expect(inv["Fn::If"][0]).toBe("UseCloudFront");
      expect(inv["Fn::If"][2]).toEqual({ Ref: "AWS::NoValue" });
    });

    it("limits concurrent builds to one per project", () => {
      expect(testProject.ConcurrentBuildLimit).toBe(1);
      expect(deployProject.ConcurrentBuildLimit).toBe(1);
    });

    it("writes test and deploy logs to separate log groups", () => {
      expect(testProject.LogsConfig.CloudWatchLogs.GroupName).toEqual({ Ref: "TestLogGroup" });
      expect(deployProject.LogsConfig.CloudWatchLogs.GroupName).toEqual({ Ref: "BuildLogGroup" });
      const logResources = (roleId: string) =>
        R[roleId].Properties.Policies.flatMap((p: any) => p.PolicyDocument.Statement)
          .filter((s: any) => s.Sid === "WriteBuildLogs")
          .map((s: any) => JSON.stringify(s.Resource));
      expect(logResources("CodeBuildTestRole")).toEqual([JSON.stringify({ "Fn::Sub": "${TestLogGroup.Arn}" })]);
      expect(logResources("CodeBuildRole")).toEqual([JSON.stringify({ "Fn::Sub": "${BuildLogGroup.Arn}" })]);
    });

    it("lets CodeBuild assume each role only for its own project in this account", () => {
      for (const [roleId, suffix] of [["CodeBuildTestRole", "-test"], ["CodeBuildRole", "-deploy"]]) {
        const stmt = R[roleId].Properties.AssumeRolePolicyDocument.Statement[0];
        expect(stmt.Condition.StringEquals["aws:SourceAccount"]).toEqual({ Ref: "AWS::AccountId" });
        expect(JSON.stringify(stmt.Condition.ArnLike["aws:SourceArn"])).toContain(`project/\${AWS::StackName}${suffix}`);
      }
    });

    it("grants no wildcard actions", () => {
      for (const roleId of ["CodeBuildTestRole", "CodeBuildRole"]) {
        for (const a of actionsOf(roleId)) expect(a).not.toContain("*");
      }
    });
  });

  describe("CloudFront (EnableCloudFront)", () => {
    it("is enabled by default and creates the delivery resources only when enabled", () => {
      expect(t.Parameters.EnableCloudFront.Default).toBe("true");
      expect(t.Parameters.EnableCloudFront.AllowedValues).toEqual(["true", "false"]);
      expect(t.Conditions.UseCloudFront).toEqual({ "Fn::Equals": [{ Ref: "EnableCloudFront" }, "true"] });
      for (const id of ["OriginAccessControl", "Certificate", "DirectoryIndexFunction", "Distribution", "AliasRecordA", "AliasRecordAAAA"]) {
        expect(R[id].Condition, id).toBe("UseCloudFront");
      }
      for (const id of ["SiteBucket", "SiteBucketPolicy", "CodeBuildProject", "CodeBuildRole", "BuildLogGroup", "CostBudget"]) {
        expect(R[id].Condition, id).toBeUndefined();
      }
    });

    it("lets CloudFront read the bucket only when enabled, and always denies plain HTTP", () => {
      const stmts = R.SiteBucketPolicy.Properties.PolicyDocument.Statement;
      const read = stmts.find((s: any) => s["Fn::If"]);
      expect(read["Fn::If"][0]).toBe("UseCloudFront");
      expect(read["Fn::If"][1].Action).toBe("s3:GetObject");
      expect(read["Fn::If"][2]).toEqual({ Ref: "AWS::NoValue" });
      expect(stmts.find((s: any) => s.Sid === "DenyInsecureTransport")).toBeDefined();
    });

    it("requires DomainName and HostedZoneId only when CloudFront is enabled", () => {
      const domain = new RegExp(t.Parameters.DomainName.AllowedPattern);
      const zone = new RegExp(t.Parameters.HostedZoneId.AllowedPattern);
      for (const ok of ["", "dev.example.com"]) expect(domain.test(ok), ok).toBe(true);
      for (const ok of ["", "Z0123456789ABCDEFGHIJ"]) expect(zone.test(ok), ok).toBe(true);
      expect(zone.test("not-a-zone")).toBe(false);
      const rule = t.Rules.DomainRequiredWithCloudFront;
      expect(rule.RuleCondition).toEqual({ "Fn::Equals": [{ Ref: "EnableCloudFront" }, "true"] });
      const asserted = JSON.stringify(rule.Assertions);
      expect(asserted).toContain('"DomainName"');
      expect(asserted).toContain('"HostedZoneId"');
    });
  });

  describe("DeployPath", () => {
    it("defaults to the bucket root and accepts only relative prefixes without empty or dot segments", () => {
      expect(t.Parameters.DeployPath.Default).toBe("");
      expect(t.Conditions.HasDeployPath).toEqual({ "Fn::Not": [{ "Fn::Equals": [{ Ref: "DeployPath" }, ""] }] });
      const re = new RegExp(t.Parameters.DeployPath.AllowedPattern);
      for (const ok of ["", "preview", "a/b-c", "v1.2/site_x"]) expect(re.test(ok), ok).toBe(true);
      for (const ng of ["../x", "/x", "x/", "a/../b", "a//b", ".", "a b"]) expect(re.test(ng), ng).toBe(false);
    });

    it("serves the DeployPath prefix at the domain root via the origin path", () => {
      const d = one("AWS::CloudFront::Distribution").Properties.DistributionConfig;
      expect(d.Origins[0].OriginPath).toEqual({
        "Fn::If": ["HasDeployPath", { "Fn::Sub": "/${DeployPath}" }, { Ref: "AWS::NoValue" }],
      });
    });
  });

  it("names the bucket from SiteBucketName when it is set", () => {
    expect(t.Parameters.SiteBucketName.Default).toBe("");
    expect(t.Conditions.HasSiteBucketName).toEqual({ "Fn::Not": [{ "Fn::Equals": [{ Ref: "SiteBucketName" }, ""] }] });
    expect(R.SiteBucket.Properties.BucketName).toEqual({
      "Fn::If": ["HasSiteBucketName", { Ref: "SiteBucketName" }, { Ref: "AWS::NoValue" }],
    });
    const re = new RegExp(t.Parameters.SiteBucketName.AllowedPattern);
    for (const ok of ["", "portfolio-site-dev", "bucket-1"]) expect(re.test(ok), ok).toBe(true);
    // ドットを含む名前は HTTPS の仮想ホスト形式で証明書が合わないため受け付けない
    for (const ng of ["UPPER", "ab", "-x-bucket", "bucket-", "my.bucket", "my..bucket", "192.168.1.1"]) {
      expect(re.test(ng), ng).toBe(false);
    }
  });

  it("alerts by email when the monthly cost approaches the budget", () => {
    const b = one("AWS::Budgets::Budget").Properties;
    expect(b.Budget.BudgetType).toBe("COST");
    expect(b.Budget.TimeUnit).toBe("MONTHLY");
    expect(b.Budget.BudgetLimit).toEqual({ Amount: { Ref: "MonthlyBudgetUsd" }, Unit: "USD" });
    expect(b.NotificationsWithSubscribers.map((n: any) => n.Notification.NotificationType).sort()).toEqual([
      "ACTUAL",
      "FORECASTED",
    ]);
    for (const n of b.NotificationsWithSubscribers) {
      expect(n.Subscribers).toEqual([{ SubscriptionType: "EMAIL", Address: { Ref: "BudgetAlertEmail" } }]);
    }
  });

  it("optionally attaches a rate-limiting WAF to the distribution", () => {
    // CloudFront を作らないときは WAF も作らない
    expect(t.Conditions.UseWaf).toEqual({
      "Fn::And": [{ "Fn::Equals": [{ Ref: "EnableWaf" }, "true"] }, { Condition: "UseCloudFront" }],
    });
    const acl = R.WebAcl;
    expect(acl.Type).toBe("AWS::WAFv2::WebACL");
    expect(acl.Condition).toBe("UseWaf");
    expect(acl.Properties.Scope).toBe("CLOUDFRONT");
    const rate = acl.Properties.Rules.find((r: any) => r.Statement.RateBasedStatement);
    expect(rate.Action).toEqual({ Block: {} });
    expect(rate.Statement.RateBasedStatement.AggregateKeyType).toBe("IP");
    const d = one("AWS::CloudFront::Distribution").Properties.DistributionConfig;
    expect(d.WebACLId).toEqual({ "Fn::If": ["UseWaf", { "Fn::GetAtt": ["WebAcl", "Arn"] }, { Ref: "AWS::NoValue" }] });
  });

  it("outputs the site url, apps base url, bucket and distribution id", () => {
    expect(Object.keys(t.Outputs).sort()).toEqual(["AppsBaseUrl", "BucketName", "DeployUri", "DistributionId", "SiteUrl"]);
    for (const k of ["AppsBaseUrl", "DistributionId", "SiteUrl"]) expect(t.Outputs[k].Condition).toBe("UseCloudFront");
    expect(JSON.stringify(t.Outputs.AppsBaseUrl.Value)).toContain("/apps/");
  });
});
