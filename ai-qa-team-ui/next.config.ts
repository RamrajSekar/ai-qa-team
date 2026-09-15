import type { NextConfig } from "next";

const apiBackendUrl = (
  process.env.API_BACKEND_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  // Allow the local browser proxy/LAN origin during development.
  allowedDevOrigins: ["192.168.23.1"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiBackendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
