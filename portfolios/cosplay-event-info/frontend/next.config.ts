import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // ポートフォリオサイトの /apps/cosplay-event-info で配信する（NF-4）。
  // portfolio-importer は basePath の直書きを検出するため、環境変数にせず固定値で書く。
  basePath: "/apps/cosplay-event-info",
  assetPrefix: "/apps/cosplay-event-info",
  trailingSlash: true,
  images: { unoptimized: true },
  // リポジトリのルートにも lockfile があるため、このディレクトリをルートとして扱う。
  turbopack: { root: dirname(fileURLToPath(import.meta.url)) },
};

export default nextConfig;
