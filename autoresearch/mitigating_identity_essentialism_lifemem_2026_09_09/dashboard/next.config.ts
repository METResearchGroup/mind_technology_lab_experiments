import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  ...(process.env.NEXT_OUTPUT === "export"
    ? { output: "export" as const, images: { unoptimized: true } }
    : {}),
};

export default nextConfig;
