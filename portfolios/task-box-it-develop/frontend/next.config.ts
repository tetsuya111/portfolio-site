import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ポートフォリオサイト（S3）で /apps/task-box-it-develop/ 配下に静的配信するための設定
  output: "export",
  basePath: "/apps/task-box-it-develop",
  trailingSlash: true,
};

export default nextConfig;
