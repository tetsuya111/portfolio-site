import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // ポートフォリオサイトの /apps/av-event-db で配信する。
  // portfolio-importer は basePath の直書きを検出するため、環境変数にせず固定値で書く。
  basePath: "/apps/av-event-db",
  assetPrefix: "/apps/av-event-db",
  trailingSlash: true,
  images: { unoptimized: true },
  // リポジトリのルートにも lockfile があるため、このディレクトリをルートとして扱う。
  turbopack: { root: dirname(fileURLToPath(import.meta.url)) },
};

export default nextConfig;
