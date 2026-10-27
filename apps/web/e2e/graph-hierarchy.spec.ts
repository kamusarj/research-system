import { expect, test } from "@playwright/test";

const root = {
  id: "concept:memory",
  type: "Concept",
  label: "Agent memory",
  summary: "Memory patterns used by business agents.",
  confidence: 1,
  source_count: 3,
  published: true,
  degree: 2,
  child_count: 1,
  lifecycle_status: "approved",
  provenance: { created_by_type: "reviewer" },
};

const research = {
  id: "research:memory",
  type: "ResearchItem",
  label: "Evidence-grounded agent memory",
  summary: "Approved research about grounded memory architectures.",
  confidence: .96,
  source_count: 1,
  published: true,
  degree: 1,
  primary_parent_id: root.id,
  child_count: 0,
  lifecycle_status: "approved",
  provenance: { created_by_type: "reviewer" },
};

const leafResearch = Array.from({ length: 12 }, (_, index) => ({
  ...research,
  id: `research:memory-${index + 1}`,
  label: `Memory evidence ${index + 1}`,
  degree: 12 - index,
}));

const unplaced = {
  id: "concept:unplaced",
  type: "Concept",
  label: "Unplaced evaluation idea",
  summary: "Approved knowledge that has no display parent yet.",
  confidence: .9,
  source_count: 1,
  published: true,
  degree: 0,
  child_count: 0,
  lifecycle_status: "approved",
  provenance: { created_by_type: "reviewer" },
};

const hierarchyGraph = {
  nodes: [{ ...root, child_count: leafResearch.length }, ...leafResearch, unplaced],
  edges: leafResearch.map((leaf, index) => ({
    id: `hierarchy:memory-research-${index + 1}`,
    source: root.id,
    target: leaf.id,
    type: "PARENT_OF",
    confidence: 1,
    evidence_count: 0,
    evidence: [],
  })),
  meta: {
    node_count: 14,
    edge_count: 12,
    total_node_count: 14,
    total_edge_count: 12,
    query: null,
    truncated: false,
    provider: "postgres",
    view: "hierarchy",
  },
};

const relationshipGraph = {
  nodes: [{ ...root, child_count: leafResearch.length }, ...leafResearch, unplaced],
  edges: leafResearch.map((leaf, index) => ({
    id: `relationship:memory-research-${index + 1}`,
    source: root.id,
    target: leaf.id,
    type: index % 2 ? "RESEARCHES" : "RELATED_TO",
    confidence: .96,
    evidence_count: 0,
    evidence: [],
  })),
  meta: { ...hierarchyGraph.meta, view: "relationship" },
};

test("research graph uses progressive hierarchy and focused relationships", async ({ page }, testInfo) => {
  if (testInfo.project.name === "desktop-chrome") {
    await page.setViewportSize({ width: 1920, height: 1080 });
  }
  const graphRequests: string[] = [];
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
    graphRequests.push(`${url.pathname}${url.search}`);
    if (url.pathname.endsWith("/graph/stats")) {
      return route.fulfill({ json: { nodes: 14, edges: 12, clusters: 2, by_type: { Concept: 2, ResearchItem: 12 } } });
    }
    return route.fulfill({
      json: url.searchParams.get("view") === "relationship" ? relationshipGraph : hierarchyGraph,
    });
  });
  await page.goto("/graph");

  await expect(page.getByRole("button", { name: "Phân cấp" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("graph-canvas")).toBeVisible();
  const viewportGeometry = await page.evaluate(() => {
    const studio = document.querySelector<HTMLElement>(".graph-studio")!;
    return {
      studioWidth: studio.getBoundingClientRect().width,
      // Cột nội dung cạnh thanh điều hướng cố định của desktop.
      contentWidth: document.querySelector<HTMLElement>("div.main")!.getBoundingClientRect().width,
      overflow: document.documentElement.scrollWidth - window.innerWidth,
    };
  });
  expect(viewportGeometry.overflow).toBeLessThanOrEqual(1);
  if (testInfo.project.name === "desktop-chrome") {
    expect(viewportGeometry.studioWidth / viewportGeometry.contentWidth).toBeGreaterThanOrEqual(.95);
  }
  await expect.poll(
    () => graphRequests.filter((request) => request.split("?")[0].endsWith("/graph")).length,
  ).toBe(2);
  expect(graphRequests.filter((request) => request.includes("/graph/stats"))).toHaveLength(0);
  await expect(page.locator(".d3-hierarchy-card")).toHaveCount(5);
  await expect(page.locator(".d3-hierarchy-relation-edge")).toHaveCount(4);
  await expect(page.locator(".graph-structure-note")).toHaveCount(0);
  await expect(page.locator('.d3-node[data-node-id="concept:memory"] .d3-hierarchy-leaf-action')).toContainText("+8 đang ẩn");
  await expect(page.locator(".graph-canvas-guide")).toHaveCount(0);
  await expect(page.locator(".graph-canvas-status")).toContainText("8 nút lá đang ẩn");
  await expect(page.locator(".graph-canvas-status")).toContainText("1 chưa xếp");
  await expect(page.getByText(/Scroll to zoom/i)).toHaveCount(0);
  await expect(page.locator('.d3-node[data-node-id="concept:unplaced"]')).toHaveCount(0);
  const lightChrome = await page.evaluate(() => {
    const studio = document.querySelector<HTMLElement>(".graph-studio");
    const canvas = document.querySelector<HTMLElement>(".graph-studio .d3-canvas");
    const icons = [...document.querySelectorAll<SVGElement>(".graph-studio .graph-toolbar svg")];
    return {
      studioBackground: studio ? getComputedStyle(studio).backgroundColor : "",
      canvasBackground: canvas ? getComputedStyle(canvas).backgroundColor : "",
      largestToolbarIcon: Math.max(0, ...icons.map((icon) => icon.getBoundingClientRect().width)),
    };
  });
  expect(lightChrome.studioBackground).toBe("rgb(255, 255, 255)");
  expect(lightChrome.canvasBackground).toBe("rgb(251, 252, 254)");
  expect(lightChrome.largestToolbarIcon).toBeLessThanOrEqual(9);

  await page.getByRole("button", { name: "Khám phá" }).click();
  await expect(page.locator(".graph-workspace")).toHaveClass(/explorer-open/);
  await expect(page.getByText("Chú giải")).toBeVisible();

  await page.locator('.d3-node[data-node-id="concept:memory"] .d3-hierarchy-leaf-action').click();
  await expect(page.locator(".d3-hierarchy-card")).toHaveCount(13);
  await expect(page.locator(".d3-hierarchy-relation-edge")).toHaveCount(12);

  await page.getByRole("button", { name: "Vừa khung", exact: true }).click();
  await page.waitForTimeout(600);
  const fittedHierarchy = await page.evaluate(() => {
    const canvas = document.querySelector<HTMLElement>('[data-testid="graph-canvas"]')!;
    const canvasRect = canvas.getBoundingClientRect();
    const outside = [...document.querySelectorAll<SVGGElement>(".d3-node")].filter((node) => {
      const rect = node.getBoundingClientRect();
      return rect.left < canvasRect.left - 1 || rect.right > canvasRect.right + 1 ||
        rect.top < canvasRect.top - 1 || rect.bottom > canvasRect.bottom + 1;
    }).length;
    const matrix = document.querySelector<SVGGElement>(".d3-graph-container")!
      .transform.baseVal.consolidate()!.matrix;
    const badge = Number(document.querySelector(".zoom-level")!.textContent!.replace("%", ""));
    return { outside, scalePercent: Math.round(matrix.a * 100), badge };
  });
  expect(fittedHierarchy.outside).toBe(0);
  expect(fittedHierarchy.badge).toBe(fittedHierarchy.scalePercent);

  await page.locator('.d3-node[data-node-id="concept:memory"]').hover();
  await expect(page.locator(".d3-hierarchy-hover-edge")).toHaveCount(24);
  const hierarchyTransitionOwners = await page.locator(".d3-node, .d3-edge").evaluateAll((elements) =>
    elements.filter((element) => "__transition" in element).length,
  );
  expect(hierarchyTransitionOwners).toBe(0);
  await page.locator(".graph-toolbar").hover();
  await expect(page.locator(".d3-hierarchy-hover-edge")).toHaveCount(0);

  await page.getByRole("button", { name: "Mạng" }).click();
  await expect(page.locator(".d3-node")).toHaveCount(14);
  expect(graphRequests.filter((request) => request.split("?")[0].endsWith("/graph"))).toHaveLength(2);
  await expect(page.getByText("Explore clustered knowledge")).toHaveCount(0);
  await expect(page.locator(".graph-canvas-status")).toContainText("cụm");
  const communityLabelLayer = await page.evaluate(() => {
    const graph = document.querySelector<SVGGElement>(".d3-graph-container")!;
    const nodes = graph.querySelector<SVGGElement>(".d3-nodes")!;
    const labels = graph.querySelector<SVGGElement>(".d3-labels")!;
    const children = [...graph.children];
    const label = labels.querySelector<SVGTextElement>(".d3-community-label")!;
    const style = getComputedStyle(label);
    return {
      count: labels.querySelectorAll(".d3-community-label").length,
      afterNodes: children.indexOf(labels) > children.indexOf(nodes),
      paintOrder: style.paintOrder,
      pointerEvents: style.pointerEvents,
      strokeWidth: Number.parseFloat(style.strokeWidth),
    };
  });
  expect(communityLabelLayer.count).toBeGreaterThan(0);
  expect(communityLabelLayer.afterNodes).toBe(true);
  expect(communityLabelLayer.paintOrder).toContain("stroke");
  expect(communityLabelLayer.pointerEvents).toBe("none");
  expect(communityLabelLayer.strokeWidth).toBeGreaterThanOrEqual(3);
  await expect(page.locator('.d3-node[data-node-id="concept:memory"] circle').first()).toHaveAttribute("r", "9.8");
  await expect(page.locator(".d3-network-edge").first()).toHaveCSS("opacity", "0.08");
  await expect(page.locator(".d3-network-edge").first()).toHaveCSS("stroke-dasharray", "3px, 7px");
  const restingVisibleLabels = await page.locator(".d3-node-label").evaluateAll((labels) =>
    labels.filter((label) => getComputedStyle(label).opacity !== "0").length,
  );
  expect(restingVisibleLabels).toBe(0);
  await expect(page.locator(".d3-node-type-label")).toHaveCount(14);
  const restingVisibleTypes = await page.locator(".d3-node-type-label").evaluateAll((labels) =>
    labels.filter((label) => getComputedStyle(label).opacity !== "0").length,
  );
  expect(restingVisibleTypes).toBe(0);

  await page.locator('.d3-node[data-node-id="concept:memory"]').hover();
  await expect(page.locator(".d3-graph-svg")).not.toHaveClass(/d3-relationship-focused/);
  await expect(page.locator('.d3-node[data-node-id="concept:memory"]')).toHaveClass(/d3-node-hovered/);
  await expect(page.locator('.d3-node[data-node-id="concept:memory"] .d3-node-label')).toHaveCSS("opacity", "1");
  await expect(page.locator('.d3-node[data-node-id="concept:memory"] .d3-node-type-label'))
    .toHaveText("KHÁI NIỆM");
  await expect(page.locator('.d3-node[data-node-id="concept:memory"] .d3-node-type-label'))
    .toHaveCSS("opacity", "1");
  await expect(page.locator(".d3-network-edge.d3-hover-edge")).toHaveCount(12);
  await expect(page.locator(".d3-network-edge.d3-hover-edge").first()).toHaveCSS("opacity", "0.92");
  await expect(page.locator(".d3-network-edge.d3-hover-edge").first()).toHaveCSS("stroke-dasharray", "none");
  const hoveredVisibleLabels = await page.locator(".d3-node-label").evaluateAll((labels) =>
    labels.filter((label) => getComputedStyle(label).opacity !== "0").length,
  );
  expect(hoveredVisibleLabels).toBe(1);
  const hoveredVisibleTypes = await page.locator(".d3-node-type-label").evaluateAll((labels) =>
    labels.filter((label) => getComputedStyle(label).opacity !== "0").length,
  );
  expect(hoveredVisibleTypes).toBe(1);
  const hoverTransitionOwners = await page.locator(".d3-node, .d3-edge").evaluateAll((elements) =>
    elements.filter((element) => "__transition" in element).length,
  );
  expect(hoverTransitionOwners).toBe(0);

  await page.locator(".graph-toolbar").hover();
  await expect(page.locator(".d3-network-edge.d3-hover-edge")).toHaveCount(0);
  await expect(page.locator(".d3-network-edge").first()).toHaveCSS("opacity", "0.08");
  const restoredVisibleLabels = await page.locator(".d3-node-label").evaluateAll((labels) =>
    labels.filter((label) => getComputedStyle(label).opacity !== "0").length,
  );
  expect(restoredVisibleLabels).toBe(0);
  const restoredVisibleTypes = await page.locator(".d3-node-type-label").evaluateAll((labels) =>
    labels.filter((label) => getComputedStyle(label).opacity !== "0").length,
  );
  expect(restoredVisibleTypes).toBe(0);

  await page.locator('.d3-node[data-node-id="concept:memory"]').click();
  await expect(page.locator(".d3-graph-svg")).toHaveClass(/d3-relationship-focused/);
  await expect(page.getByTestId("node-details")).toContainText("Agent memory");
  await expect(page.locator('.d3-node[data-node-id="concept:unplaced"]')).toHaveCSS("opacity", "0.12");
  await expect(page.locator('.d3-node[data-node-id="research:memory-1"]')).toHaveCSS("opacity", "0.9");
  await page.locator(".graph-toolbar").hover();
  const selectedVisibleLabels = await page.locator(".d3-node-label").evaluateAll((labels) =>
    labels.filter((label) => getComputedStyle(label).opacity !== "0").length,
  );
  expect(selectedVisibleLabels).toBe(0);
  const selectedVisibleTypes = await page.locator(".d3-node-type-label").evaluateAll((labels) =>
    labels.filter((label) => getComputedStyle(label).opacity !== "0").length,
  );
  expect(selectedVisibleTypes).toBe(0);

  await page.getByRole("button", { name: "Quỹ đạo" }).click();
  await expect(page.locator(".d3-orbit-ring")).toHaveCount(4);
  await expect(page.locator(".d3-node")).toHaveCount(14);
  await expect(page.locator(".d3-node-type-label")).toHaveCount(0);

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
});
