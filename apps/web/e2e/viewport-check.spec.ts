import { expect, test } from "@playwright/test";

/**
 * Check the graph workspace at three viewports for the failures C7 names: the page
 * scrolling sideways, labels overflowing their nodes, and controls landing off screen.
 * Auth and graph data are mocked so the layout contract can be measured in any
 * environment (including one with AUTH_MODE=local) without touching real data.
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 834, height: 1112 },
  { name: "mobile", width: 390, height: 844 },
];

const layoutGraph = (view: string) => ({
  nodes: [
    {
      id: "concept:memory",
      type: "Concept",
      label: "Agent memory",
      summary: "Memory patterns used by business agents.",
      confidence: 1,
      source_count: 3,
      published: true,
      degree: 4,
      child_count: 2,
      lifecycle_status: "approved",
      provenance: { created_by_type: "reviewer" },
    },
    {
      id: "research:grounding",
      type: "ResearchItem",
      label: "Evidence-grounded agent memory architectures",
      summary: "Approved research about grounded memory.",
      confidence: 0.96,
      source_count: 1,
      published: true,
      degree: 1,
      primary_parent_id: "concept:memory",
      child_count: 0,
      lifecycle_status: "approved",
      provenance: { created_by_type: "reviewer" },
    },
    {
      id: "concept:approval",
      type: "Concept",
      label: "Human approval improves reliability của hệ thống",
      summary: "Approval workflows.",
      confidence: 0.9,
      source_count: 2,
      published: true,
      degree: 2,
      primary_parent_id: "concept:memory",
      child_count: 0,
      lifecycle_status: "approved",
      provenance: { created_by_type: "reviewer" },
    },
  ],
  edges: [
    {
      id: "edge:memory-grounding",
      source: "concept:memory",
      target: "research:grounding",
      type: "PARENT_OF",
      confidence: 1,
      evidence_count: 0,
      evidence: [],
    },
    {
      id: "edge:memory-approval",
      source: "concept:memory",
      target: "concept:approval",
      type: "PARENT_OF",
      confidence: 1,
      evidence_count: 0,
      evidence: [],
    },
    {
      id: "edge:grounding-approval",
      source: "research:grounding",
      target: "concept:approval",
      type: "RELATED_TO",
      confidence: 0.9,
      evidence_count: 1,
      evidence: [],
    },
  ],
  meta: {
    node_count: 3,
    edge_count: 3,
    total_node_count: 3,
    total_edge_count: 3,
    query: null,
    truncated: false,
    provider: "postgres",
    view,
  },
});

for (const viewport of VIEWPORTS) {
  test(`graph workspace holds together at ${viewport.name}`, async ({ page }, testInfo) => {
    const consoleErrors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });

    await page.route("**/api/v1/auth/config", (route) => route.fulfill({
      json: { enabled: false, mode: "local", csrf_cookie_name: "research_csrf" },
    }));
    await page.route("**/api/v1/auth/me", (route) => route.fulfill({
      json: {
        enabled: false,
        user: {
          id: "local-user",
          name: "Local owner",
          email: "local@research.system",
          role: "owner",
          active: true,
          password_configured: false,
        },
      },
    }));
    await page.route("**/api/v1/graph**", (route) => {
      const url = new URL(route.request().url());
      return route.fulfill({ json: layoutGraph(url.searchParams.get("view") ?? "hierarchy") });
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
      path: testInfo.outputPath(`graph-${viewport.name}.png`),
      fullPage: false,
    });

    expect(consoleErrors, `console errors at ${viewport.name}`).toEqual([]);
  });
}
