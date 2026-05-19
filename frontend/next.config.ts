import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: "50mb",
    },
    proxyClientMaxBodySize: "50mb",
  },
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
