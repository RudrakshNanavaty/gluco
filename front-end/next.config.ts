import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The README documents both localhost and 127.0.0.1. Permit the latter to
  // load development-only HMR resources without cross-origin warnings.
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
