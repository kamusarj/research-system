import type { NextConfig } from "next";

const apiProxyTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";
export const DEFAULT_API_PROXY_TIMEOUT_MS = 180_000;

export function resolveApiProxyTimeout(value = process.env.API_PROXY_TIMEOUT_MS): number {
  const configured = Number.parseInt(value ?? String(DEFAULT_API_PROXY_TIMEOUT_MS), 10);
  return Number.isFinite(configured) && configured > 0
    ? configured
    : DEFAULT_API_PROXY_TIMEOUT_MS;
}

const apiProxyTimeout = resolveApiProxyTimeout();

// Header bảo vệ cơ bản cho mọi trang và cả phản hồi API đi qua proxy. HSTS/TLS do lớp
// Caddy/Cloudflare phía trước đảm nhận vì chế độ cục bộ vẫn chạy bằng HTTP.
export const SECURITY_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
  experimental: {
    // HTTPX's 120-second provider timeout is an inactivity timeout, not a total wall-clock
    // deadline. A real successful DeepSeek edit took 131.1 seconds, so keep a bounded 180-second
    // browser proxy budget rather than resetting a valid in-flight response at 125 seconds.
    proxyTimeout: apiProxyTimeout,
  },
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${apiProxyTarget}/api/v1/:path*` }];
  },
};
export default nextConfig;
