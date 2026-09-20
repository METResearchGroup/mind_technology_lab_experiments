import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingIncludes: {
    "/api/session": ["./ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md"],
  },
};

export default nextConfig;
