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
      "BackendDomainName",
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
      "ItArticlesPerRun",
      "ItArticlesScheduleExpression",
      "ItArticlesScheduleState",
      "MonthlyBudgetUsd",
      "PerplexityApiKeyParameterName",
      "PerplexityModel",
      "SecurityArticlesPerRun",
      "SiteBucketName",
    ]);
    // 未指定（空）なら任意のブランチへの push でデプロイする
    expect(t.Parameters.DeployBranch.Default).toBe("");
    expect(t.Conditions.HasDeployBranch).toEqual({ "Fn::Not": [{ "Fn::Equals": [{ Ref: "DeployBranch" }, ""] }] });
    expect(t.Parameters.GitHubActorAccountId.AllowedPattern).toBe("^[0-9]+$");
    expect(t.Parameters.EnableWaf.AllowedValues).toEqual(["true", "false"]);
  });

  it("uses unique logical ids across parameters, resources and outputs", () => {
    // CloudFormation では Parameters・Resources・Outputs の論理 ID が重なるとテンプレートが拒否される
    const ids = [...Object.keys(t.Parameters), ...Object.keys(t.Resources), ...Object.keys(t.Outputs)];
    expect(ids.filter((id, i) => ids.indexOf(id) !== i)).toEqual([]);
  });

  it("requires us-east-1", () => {
    const assertions = Object.values(t.Rules).flatMap((r: any) => r.Assertions);
    expect(JSON.stringify(assertions)).toContain('"AWS::Region"');
    expect(JSON.stringify(assertions)).toContain('"us-east-1"');
  });

  it("keeps the bucket private and encrypted", () => {
    const b = R.SiteBucket.Properties;
    expect(b.PublicAccessBlockConfiguration).toEqual({
      BlockPublicAcls: true,
      BlockPublicPolicy: true,
      IgnorePublicAcls: true,
      RestrictPublicBuckets: true,
    });
    expect(b.BucketEncryption).toBeDefined();
  });

  it("allows only CloudFront of this distribution to read the bucket", () => {
    const stmts = R.SiteBucketPolicy.Properties.PolicyDocument.Statement;
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
    expect(R.DirectoryIndexFunction.Properties.FunctionCode).toContain("index.html");
    const d = one("AWS::CloudFront::Distribution").Properties.DistributionConfig;
    expect(d.Aliases).toEqual([{ Ref: "DomainName" }]);
    expect(d.DefaultCacheBehavior.ViewerProtocolPolicy).toBe("redirect-to-https");
    expect(d.ViewerCertificate.MinimumProtocolVersion).toBe("TLSv1.2_2021");
    expect(d.ViewerCertificate.SslSupportMethod).toBe("sni-only");
    expect(d.Origins[0].OriginAccessControlId).toBeDefined();
    expect(d.DefaultCacheBehavior.FunctionAssociations[0].EventType).toBe("viewer-request");
    // 404 だけを 404 ページにする（403 はバックエンドの CSRF の拒否などをそのまま返すため置き換えない）
    const paged = d.CustomErrorResponses.filter((e: any) => e.ResponsePagePath);
    expect(paged).toEqual([{ ErrorCode: 404, ResponseCode: 404, ResponsePagePath: "/404.html", ErrorCachingMinTTL: 0 }]);
  });

  it("does not cache backend errors and does not replace them with the 404 page", () => {
    const d = one("AWS::CloudFront::Distribution").Properties.DistributionConfig;
    const unpaged = d.CustomErrorResponses.filter((e: any) => !e.ResponsePagePath);
    // CloudFront が既定でキャッシュするエラーコードすべて
    expect(unpaged.map((e: any) => e.ErrorCode)).toEqual([400, 403, 405, 414, 416, 500, 501, 502, 503, 504]);
    for (const e of unpaged) {
      expect(e.ErrorCachingMinTTL).toBe(0);
      expect(e.ResponseCode).toBeUndefined();
    }
  });

  it("lets CloudFront list the bucket so missing keys are 404, not 403", () => {
    const stmts = R.SiteBucketPolicy.Properties.PolicyDocument.Statement;
    const conditional = stmts.filter((s: any) => s["Fn::If"]).map((s: any) => s["Fn::If"]);
    const list = conditional.find((c: any) => c[1].Action === "s3:ListBucket");
    expect(list[0]).toBe("UseCloudFront");
    expect(list[2]).toEqual({ Ref: "AWS::NoValue" });
    expect(list[1].Principal).toEqual({ Service: "cloudfront.amazonaws.com" });
    expect(list[1].Resource).toEqual({ "Fn::GetAtt": ["SiteBucket", "Arn"] });
    const read = conditional.find((c: any) => c[1].Action === "s3:GetObject");
    expect(list[1].Condition).toEqual(read[1].Condition);
  });

  describe("backend origin (BackendDomainName)", () => {
    const d = R.Distribution.Properties.DistributionConfig;
    const PREFIX = "/apps/spotify-billboard-playlist";

    it("is off by default and only with CloudFront", () => {
      expect(t.Parameters.BackendDomainName.Default).toBe("");
      const re = new RegExp(t.Parameters.BackendDomainName.AllowedPattern);
      for (const ok of ["", "vps.example.com"]) expect(re.test(ok), ok).toBe(true);
      for (const ng of ["https://vps.example.com", "vps.example.com/x", "VPS.example.com", "localhost"]) {
        expect(re.test(ng), ng).toBe(false);
      }
      expect(t.Conditions.UseBackend).toEqual({
        "Fn::And": [{ Condition: "UseCloudFront" }, { "Fn::Not": [{ "Fn::Equals": [{ Ref: "BackendDomainName" }, ""] }] }],
      });
      expect(R.BackendPathFunction.Condition).toBe("UseBackend");
    });

    it("adds the VPS as an https-only origin with a 60 second read timeout", () => {
      const origin = d.Origins.find((o: any) => o["Fn::If"])["Fn::If"];
      expect(origin[0]).toBe("UseBackend");
      expect(origin[2]).toEqual({ Ref: "AWS::NoValue" });
      expect(origin[1].Id).toBe("BackendOrigin");
      expect(origin[1].DomainName).toEqual({ Ref: "BackendDomainName" });
      expect(origin[1].CustomOriginConfig).toMatchObject({
        HTTPSPort: 443,
        OriginProtocolPolicy: "https-only",
        OriginSSLProtocols: ["TLSv1.2"],
        OriginReadTimeout: 60,
      });
    });

    it("forwards the api and auth paths without caching, with cookies and all methods", () => {
      const [cond, behaviors, none] = d.CacheBehaviors["Fn::If"];
      expect(cond).toBe("UseBackend");
      expect(none).toEqual({ Ref: "AWS::NoValue" });
      expect(behaviors.map((b: any) => b.PathPattern)).toEqual([`${PREFIX}/api/*`, `${PREFIX}/auth/*`]);
      for (const b of behaviors) {
        expect(b.TargetOriginId).toBe("BackendOrigin");
        expect(b.ViewerProtocolPolicy).toBe("https-only");
        expect([...b.AllowedMethods].sort()).toEqual(["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]);
        // マネージドポリシー: CachingDisabled / AllViewerExceptHostHeader / SecurityHeadersPolicy
        expect(b.CachePolicyId).toBe("4135ea2d-6df8-44a3-9df3-4b5a84be39ad");
        expect(b.OriginRequestPolicyId).toBe("b689b0a8-53d0-40ab-baf2-68738e2966ac");
        expect(b.ResponseHeadersPolicyId).toBe(d.DefaultCacheBehavior.ResponseHeadersPolicyId);
        // CachingDisabled は圧縮を有効にしないため、Compress を付けても効かない
        expect(b.Compress).toBeUndefined();
        expect(b.FunctionAssociations).toEqual([
          { EventType: "viewer-request", FunctionARN: { "Fn::GetAtt": ["BackendPathFunction", "FunctionMetadata.FunctionARN"] } },
        ]);
      }
    });

    it("strips /apps from the path so the VPS nginx sees /<slug>/...", () => {
      const handler = new Function(`${R.BackendPathFunction.Properties.FunctionCode}; return handler;`)();
      const run = (uri: string) => handler({ request: { uri } }).uri;
      expect(run(`${PREFIX}/api/me`)).toBe("/spotify-billboard-playlist/api/me");
      expect(run(`${PREFIX}/auth/callback`)).toBe("/spotify-billboard-playlist/auth/callback");
      expect(run("/other/apps/x")).toBe("/other/apps/x");
    });
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
      expect(ofType("AWS::CodeBuild::Project")).toHaveLength(3);
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
      expect(Object.keys(env).sort()).toEqual(["DEPLOY_BRANCH", "DEPLOY_PATH", "DISTRIBUTION_ID", "IT_ARTICLES_BUCKET", "SITE_BUCKET"]);
      // 定期実行で作った IT 記事を、push のデプロイでも取り込む（buildspec.yml の pre_build）
      expect(env.IT_ARTICLES_BUCKET).toEqual({ Ref: "ItArticlesBucket" });
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
      for (const roleId of ["CodeBuildTestRole", "CodeBuildRole", "ItArticlesRole", "ItArticlesSchedulerRole"]) {
        for (const a of actionsOf(roleId)) expect(a).not.toContain("*");
      }
    });
  });

  describe("IT 記事の定期作成", () => {
    const project = R.ItArticlesProject?.Properties;
    const schedule = R.ItArticlesSchedule?.Properties;
    const stmts = (roleId: string): any[] =>
      R[roleId].Properties.Policies.flatMap((p: any) => p.PolicyDocument.Statement)
        .flatMap((s: any) => (s["Fn::If"] ? s["Fn::If"].slice(1) : [s]))
        .filter((s: any) => s.Ref !== "AWS::NoValue");
    const actions = (roleId: string): string[] => stmts(roleId).flatMap((s: any) => [s.Action].flat());

    it("declares the schedule parameters (daily, off until the API key is registered, 5 articles)", () => {
      const P = t.Parameters;
      expect(P.ItArticlesScheduleExpression.Default).toBe("rate(1 day)");
      expect(P.ItArticlesScheduleState.Default).toBe("DISABLED");
      expect(P.ItArticlesScheduleState.AllowedValues).toEqual(["ENABLED", "DISABLED"]);
      expect(P.ItArticlesPerRun.Default).toBe(5);
      expect(P.ItArticlesPerRun.MinValue).toBe(1);
      expect(P.ItArticlesPerRun.MaxValue).toBe(10);
      expect(P.PerplexityModel.Default).toBe("sonar");
      expect(P.PerplexityModel.AllowedValues).toEqual(["sonar", "sonar-pro"]);
      expect(P.PerplexityApiKeyParameterName.Default).toBe("/portfolio-site/perplexity-api-key");
      const re = new RegExp(P.PerplexityApiKeyParameterName.AllowedPattern);
      expect(re.test("/portfolio-site/perplexity-api-key")).toBe(true);
      for (const ng of ["no-slash", "/a b", ""]) expect(re.test(ng), ng).toBe(false);
    });

    it("declares the number of security articles per run (3 by default, 0 turns it off)", () => {
      const p = t.Parameters.SecurityArticlesPerRun;
      expect(p.Type).toBe("Number");
      expect(p.Default).toBe(3);
      expect(p.MinValue).toBe(0);
      expect(p.MaxValue).toBe(10);
      const env = project.Environment.EnvironmentVariables.find((v: any) => v.Name === "SECURITY_ARTICLES_PER_RUN");
      expect(env).toEqual({ Name: "SECURITY_ARTICLES_PER_RUN", Value: { Ref: "SecurityArticlesPerRun" } });
    });

    it("limits both roles to the it-articles/ and security-articles/ prefixes of the article bucket", () => {
      for (const roleId of ["CodeBuildRole", "ItArticlesRole"]) {
        const s = stmts(roleId).filter((x: any) => JSON.stringify(x.Resource).includes("ItArticlesBucket"));
        const list = s.find((x: any) => x.Action === "s3:ListBucket");
        expect(list.Condition.StringLike["s3:prefix"], roleId).toEqual(["it-articles/*", "security-articles/*"]);
        const objects = s.find((x: any) => x.Action !== "s3:ListBucket");
        expect(objects.Resource, roleId).toEqual([
          { "Fn::Sub": "${ItArticlesBucket.Arn}/it-articles/*" },
          { "Fn::Sub": "${ItArticlesBucket.Arn}/security-articles/*" },
        ]);
      }
    });

    it("keeps the article bucket private, encrypted, versioned and retained", () => {
      const b = R.ItArticlesBucket;
      expect(b.DeletionPolicy).toBe("Retain");
      expect(b.Properties.PublicAccessBlockConfiguration).toEqual(R.SiteBucket.Properties.PublicAccessBlockConfiguration);
      expect(b.Properties.BucketEncryption).toBeDefined();
      expect(b.Properties.VersioningConfiguration).toEqual({ Status: "Enabled" });
      expect(JSON.stringify(R.ItArticlesBucketPolicy.Properties.PolicyDocument)).toContain("aws:SecureTransport");
    });

    it("runs the IT article buildspec without a webhook, one build at a time", () => {
      expect(project.Name).toEqual({ "Fn::Sub": "${AWS::StackName}-it-articles" });
      expect(project.Source.BuildSpec).toBe("portfolio-site/buildspec.it-articles.yml");
      expect(project.Source.Type).toBe("GITHUB");
      expect(project.Triggers).toBeUndefined();
      expect(project.ConcurrentBuildLimit).toBe(1);
      expect(project.SourceVersion).toEqual({ "Fn::If": ["HasDeployBranch", { Ref: "DeployBranch" }, { Ref: "AWS::NoValue" }] });
      expect(project.ServiceRole).toEqual({ "Fn::GetAtt": ["ItArticlesRole", "Arn"] });
    });

    it("passes the API key from SSM Parameter Store, never as plain text", () => {
      const env = project.Environment.EnvironmentVariables;
      const key = env.find((v: any) => v.Name === "PERPLEXITY_API_KEY");
      expect(key).toEqual({ Name: "PERPLEXITY_API_KEY", Type: "PARAMETER_STORE", Value: { Ref: "PerplexityApiKeyParameterName" } });
      const names = env.map((v: any) => v.Name).sort();
      expect(names).toEqual([
        "DEPLOY_PATH",
        "DISTRIBUTION_ID",
        "IT_ARTICLES_BUCKET",
        "IT_ARTICLES_PER_RUN",
        "PERPLEXITY_API_KEY",
        "PERPLEXITY_MODEL",
        "SECURITY_ARTICLES_PER_RUN",
        "SITE_BUCKET",
      ]);
    });

    it("gives the IT article role no delete permission and only its own SSM parameter", () => {
      expect(actions("ItArticlesRole")).not.toContain("s3:DeleteObject");
      const ssm = stmts("ItArticlesRole").find((s: any) => [s.Action].flat().includes("ssm:GetParameters"));
      expect(ssm.Resource).toEqual({
        "Fn::Sub": "arn:${AWS::Partition}:ssm:${AWS::Region}:${AWS::AccountId}:parameter${PerplexityApiKeyParameterName}",
      });
      const stmt = R.ItArticlesRole.Properties.AssumeRolePolicyDocument.Statement[0];
      expect(stmt.Condition.StringEquals["aws:SourceAccount"]).toEqual({ Ref: "AWS::AccountId" });
      expect(JSON.stringify(stmt.Condition.ArnLike["aws:SourceArn"])).toContain("project/${AWS::StackName}-it-articles");
    });

    it("starts the build on the schedule in Asia/Tokyo, with the state from the parameter", () => {
      expect(schedule.ScheduleExpression).toEqual({ Ref: "ItArticlesScheduleExpression" });
      expect(schedule.ScheduleExpressionTimezone).toBe("Asia/Tokyo");
      // DeployBranch が空だと、push のデプロイ（任意のブランチ）と定期実行（デフォルトブランチ）で公開する内容が食い違うため、常に OFF にする
      expect(schedule.State).toEqual({ "Fn::If": ["HasDeployBranch", { Ref: "ItArticlesScheduleState" }, "DISABLED"] });
      expect(schedule.FlexibleTimeWindow).toEqual({ Mode: "OFF" });
      expect(schedule.Target.Arn).toBe("arn:aws:scheduler:::aws-sdk:codebuild:startBuild");
      expect(schedule.Target.RoleArn).toEqual({ "Fn::GetAtt": ["ItArticlesSchedulerRole", "Arn"] });
      expect(JSON.stringify(schedule.Target.Input)).toContain("ProjectName");
    });

    it("lets the scheduler start only the IT article project", () => {
      const s = stmts("ItArticlesSchedulerRole");
      expect(s).toHaveLength(1);
      expect(s[0].Action).toBe("codebuild:StartBuild");
      expect(s[0].Resource).toEqual({ "Fn::GetAtt": ["ItArticlesProject", "Arn"] });
      expect(R.ItArticlesSchedulerRole.Properties.AssumeRolePolicyDocument.Statement[0].Principal).toEqual({
        Service: "scheduler.amazonaws.com",
      });
    });

    it("lets the push deploy read (not write) the article bucket", () => {
      const read = stmts("CodeBuildRole").filter((s: any) => JSON.stringify(s.Resource).includes("ItArticlesBucket"));
      expect(read.flatMap((s: any) => [s.Action].flat()).sort()).toEqual(["s3:GetObject", "s3:ListBucket"]);
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

  it("outputs the site url, apps base url, buckets, the IT article project and distribution id", () => {
    expect(Object.keys(t.Outputs).sort()).toEqual([
      "AppsBaseUrl",
      "BucketName",
      "DeployUri",
      "DistributionId",
      "ItArticlesBucketName",
      "ItArticlesProjectName",
      "SiteUrl",
    ]);
    for (const k of ["AppsBaseUrl", "DistributionId", "SiteUrl"]) expect(t.Outputs[k].Condition).toBe("UseCloudFront");
    expect(JSON.stringify(t.Outputs.AppsBaseUrl.Value)).toContain("/apps/");
  });
});
