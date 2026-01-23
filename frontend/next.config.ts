import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://backend-api:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
