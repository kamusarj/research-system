import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  outputDir: process.env.PLAYWRIGHT_OUTPUT_DIR ?? "/tmp/business-ai-agents-playwright-results",
  timeout: 30_000,
  fullyParallel: false,
  // Every case drives the same backend and mutates its data, so they cannot safely run
  // beside each other. `fullyParallel: false` only serialises within a file — without a
  // single worker, files still race across projects and the suite fails intermittently.
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    channel: "chrome",
    headless: true,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop-chrome", use: { ...devices["Desktop Chrome"] } },
    { name: "tablet-chrome", use: { viewport: { width: 1024, height: 768 } } },
    { name: "mobile-chrome", use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
});
