import { PHASE_DEVELOPMENT_SERVER } from "next/constants";
import type { NextConfig } from "next";

// 開発サーバー: /api と /auth をバックエンド(FastAPI)へ転送し、ブラウザからは同一オリジンに見せる。
// ビルド: ポートフォリオサイト（S3）の /apps/spotify-billboard-playlist/ で配信する静的ファイルを出力する。
//   rewrites は静的出力では使えないため付けない。API・認証は basePath の下のパスで呼び、
//   サイトの CloudFront が VPS のバックエンドへ転送する（apps.json で mock: true ならモックが応答する）。
const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
const BASE_PATH = "/apps/spotify-billboard-playlist";

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
    basePath: BASE_PATH,
    // lib/api.ts が API・認証のパスの先頭に付ける（fetch や <a> には basePath が自動で付かないため）
    env: { NEXT_PUBLIC_BASE_PATH: BASE_PATH },
    trailingSlash: true,
  };
}
