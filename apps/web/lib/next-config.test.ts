import { expect, it } from "vitest";
import nextConfig, {
  contentSecurityPolicy,
  DEFAULT_API_PROXY_TIMEOUT_MS,
  SECURITY_HEADERS,
  resolveApiProxyTimeout,
} from "../next.config";

it("keeps the API proxy alive beyond the observed successful provider duration", () => {
  expect(DEFAULT_API_PROXY_TIMEOUT_MS).toBe(180_000);
  expect(nextConfig.experimental?.proxyTimeout).toBe(180_000);
  expect(nextConfig.experimental?.proxyTimeout).toBeGreaterThan(131_115);
});

it("supports a positive deployment override and fails invalid values back to the safe default", () => {
  expect(resolveApiProxyTimeout("210000")).toBe(210_000);
  expect(resolveApiProxyTimeout("0")).toBe(DEFAULT_API_PROXY_TIMEOUT_MS);
  expect(resolveApiProxyTimeout("invalid")).toBe(DEFAULT_API_PROXY_TIMEOUT_MS);
});

it("applies baseline security headers to every route and hides the framework banner", async () => {
  expect(nextConfig.poweredByHeader).toBe(false);
  const rules = await nextConfig.headers!();
  expect(rules).toEqual([{ source: "/:path*", headers: SECURITY_HEADERS }]);
  expect(SECURITY_HEADERS.map((header) => header.key)).toContain("X-Content-Type-Options");
});

it("ships a CSP that blocks foreign scripts, exfiltration and framing", () => {
  const production = contentSecurityPolicy(false, "/api/v1");
  expect(production).toContain("default-src 'self'");
  expect(production).toContain("connect-src 'self';");
  expect(production).toContain("frame-ancestors 'self'");
  expect(production).toContain("base-uri 'self'");
  expect(production).not.toContain("unsafe-eval");
  expect(production).not.toMatch(/script-src[^;]*https:/);
  const separateApi = contentSecurityPolicy(false, "https://api.example.com/api/v1");
  expect(separateApi).toContain("connect-src 'self' https://api.example.com");
  expect(separateApi).toContain("frame-src 'self' blob: https://api.example.com");
  expect(contentSecurityPolicy(true, undefined)).toContain("'unsafe-eval'");
  expect(SECURITY_HEADERS.map((header) => header.key)).toContain("Content-Security-Policy");
});
