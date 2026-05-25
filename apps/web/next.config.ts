import type { NextConfig } from "next";
import path from "node:path";

const FASTAPI_ORIGIN = process.env.FASTAPI_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${FASTAPI_ORIGIN}/api/:path*` },
    ];
  },
};

export default nextConfig;
