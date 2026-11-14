import { PHASE_DEVELOPMENT_SERVER } from "next/constants";
import type { NextConfig } from "next";

// 開発サーバー: /api と /auth をバックエンド(FastAPI)へ転送し、ブラウザからは同一オリジンに見せる。
// ビルド: ポートフォリオサイト（S3）の /apps/spotify-billboard-playlist/ で配信する静的ファイルを出力する。
//   rewrites は静的出力では使えないため付けない（API はサイト側のモックが fetch を横取りして応答する）。
const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export default function nextConfig(phase: string): NextConfig {
  if (phase === PHASE_DEVELOPMENT_SERVER) {
    return {
      async rewrites() {
        return [
          { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
          { source: "/auth/:path*", destination: `${backendUrl}/auth/:path*` },
        ];
      },
    };
  }
  return {
    output: "export",
    basePath: "/apps/spotify-billboard-playlist",
    trailingSlash: true,
  };
}
