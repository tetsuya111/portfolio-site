import type { NextConfig } from "next";

// /api と /auth をバックエンド(FastAPI)へ転送し、ブラウザからは同一オリジンに見せる。
const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
      { source: "/auth/:path*", destination: `${backendUrl}/auth/:path*` },
    ];
  },
};

export default nextConfig;
