import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";

// サブパス配信（例: /apps/inventory-management）に対応する。未設定ならルートで配信する。
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig: NextConfig = {
  output: "export",
  basePath,
  assetPrefix: basePath || undefined,
  trailingSlash: true,
  images: { unoptimized: true },
  // リポジトリのルートにも lockfile があるため、このディレクトリをルートとして扱う。
  turbopack: { root: dirname(fileURLToPath(import.meta.url)) },
};

export default nextConfig;
