import { expect, it } from "vitest";
import nextConfig, {
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
