import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: "20mb",
    },
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          // Prevent the app from being embedded in an iframe (clickjacking)
          { key: "X-Frame-Options", value: "DENY" },
          // Prevent MIME-type sniffing
          { key: "X-Content-Type-Options", value: "nosniff" },
          // Don't send full URL as referrer to third parties
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // Disable unused browser features
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
