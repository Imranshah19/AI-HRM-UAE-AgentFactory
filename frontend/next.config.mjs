/** @type {import('next').NextConfig} */
const nextConfig = {
  // ── Standalone output for Docker production builds ─────────────────────
  output: "standalone",

  // ── TypeScript & ESLint ──────────────────────────────────────────────────
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },

  // ── Images ────────────────────────────────────────────────────────────────
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/uploads/**",
      },
      {
        protocol: "https",
        hostname: "*.amazonaws.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "*.s3.amazonaws.com",
        pathname: "/**",
      },
    ],
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
  },

  // ── API Proxy (rewrites /api/* → backend:8000) ────────────────────────────
  // BACKEND_INTERNAL_URL is set to http://backend:8000 inside Docker so that
  // server-side rewrites (including WebSocket upgrades) reach the backend
  // container instead of resolving localhost to the frontend container itself.
  async rewrites() {
    const backendUrl =
      process.env.BACKEND_INTERNAL_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },

  // ── Security Headers ──────────────────────────────────────────────────────
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options",   value: "nosniff" },
          { key: "X-Frame-Options",           value: "DENY" },
          { key: "X-XSS-Protection",          value: "1; mode=block" },
          { key: "Referrer-Policy",           value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(self), payment=()",
          },
        ],
      },
    ];
  },

  // ── Compiler Options ──────────────────────────────────────────────────────
  compiler: {
    removeConsole: process.env.NODE_ENV === "production"
      ? { exclude: ["error", "warn"] }
      : false,
  },

  // ── Experimental ──────────────────────────────────────────────────────────
  experimental: {
    serverComponentsExternalPackages: ["@node-rs/argon2"],
  },
};

export default nextConfig;
