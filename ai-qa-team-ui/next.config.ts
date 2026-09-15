import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow the local browser proxy/LAN origin during development.
  allowedDevOrigins: ["192.168.23.1"],
};

export default nextConfig;
