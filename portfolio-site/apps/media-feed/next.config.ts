import type { NextConfig } from "next";

// ポートフォリオサイト（S3）で /apps/media-feed/ 配下に静的配信するための設定。
// 静的出力では headers・rewrites・middleware が使えないため外し、API はブラウザ内のモック
// （portfolio-site/apps/media-feed/mock/handlers.js）が応答する。
const nextConfig: NextConfig = {
  output: "export",
  basePath: "/apps/media-feed",
  trailingSlash: true,
  // 静的出力では画像最適化サーバーがないため、next/image は元の画像をそのまま使う
  images: { unoptimized: true },
  env: {
    // Turnstile（bot 対策）はサイトキー・検証 API がないため無効にする
    NEXT_PUBLIC_TURNSTILE_ENABLED: "false",
  },
};

export default nextConfig;
