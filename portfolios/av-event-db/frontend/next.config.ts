import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";

// 開発サーバーは localhost 以外のホストからの JS・HMR の読み込みを拒否するため、
// 127.0.0.1 や LAN の IP で開くと画面が動かない（ボタンが反応しない）。
// 127.0.0.1 は常に許可し、ほかのホストは NEXT_DEV_ALLOWED_ORIGINS（カンマ区切り）で追加する。
const allowedDevOrigins = [
  "127.0.0.1",
  ...(process.env.NEXT_DEV_ALLOWED_ORIGINS ?? "")
    .split(",")
    .map((h) => h.trim())
    .filter(Boolean),
];

const nextConfig: NextConfig = {
  allowedDevOrigins,
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
