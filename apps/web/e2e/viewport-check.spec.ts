import { expect, test } from "@playwright/test";

/**
 * Check the graph workspace at three viewports for the failures C7 names: the page
 * scrolling sideways, labels overflowing their nodes, and controls landing off screen.
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 834, height: 1112 },
  { name: "mobile", width: 390, height: 844 },
];

for (const viewport of VIEWPORTS) {
  test(`graph workspace holds together at ${viewport.name}`, async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });

    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/graph", { waitUntil: "networkidle" });
    await expect(page.getByTestId("graph-canvas")).toBeVisible({ timeout: 20000 });
    // The fit-to-screen zoom is a 500ms transition; assert once it has settled.
    await expect
      .poll(async () => {
        const first = await page.evaluate(
          () => document.querySelector(".d3-canvas svg > g")?.getAttribute("transform") ?? "",
        );
        await new Promise((resolve) => setTimeout(resolve, 250));
        const second = await page.evaluate(
          () => document.querySelector(".d3-canvas svg > g")?.getAttribute("transform") ?? "",
        );
        return first !== "" && first === second;
      }, { timeout: 15000 })
      .toBe(true);

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow, "page must not scroll horizontally").toBeLessThanOrEqual(1);

    // Every node label must stay inside the canvas box it belongs to.
    const escaping = await page.evaluate(() => {
      const canvas = document.querySelector(".d3-canvas")?.getBoundingClientRect();
      if (!canvas) return 0;
      return [...document.querySelectorAll(".d3-node text")].filter((label) => {
        const box = label.getBoundingClientRect();
        return box.width > 0 && (box.left < canvas.left - 2 || box.right > canvas.right + 2);
      }).length;
    });
    expect(escaping, "node labels must stay inside the canvas").toBe(0);

    const zoomControls = page.locator(".zoom-controls");
    await expect(zoomControls).toBeVisible();
    const box = await zoomControls.boundingBox();
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1);

    await page.screenshot({
      path: `/tmp/claude-1000/-run-media-linh-Data-Shared2OS-Business-AI-Agents/cc525e01-d714-4467-8e06-4d071dac3df3/scratchpad/graph-${viewport.name}.png`,
      fullPage: false,
    });

    expect(consoleErrors, `console errors at ${viewport.name}`).toEqual([]);
  });
}
