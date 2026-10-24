import { expect, it } from "vitest";
import playwrightConfig from "../playwright.config";

it("writes browser artifacts outside potentially root-owned workspace output", () => {
  expect(playwrightConfig.outputDir).toBe(
    process.env.PLAYWRIGHT_OUTPUT_DIR ?? "/tmp/business-ai-agents-playwright-results",
  );
});
