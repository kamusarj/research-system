import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/config", (route) => route.fulfill({
    json: { enabled: false, mode: "local", csrf_cookie_name: "research_csrf" },
  }));
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({
    json: {
      enabled: false,
      user: {
        id: "local-user",
        name: "Người quản lý cục bộ",
        email: "local@research.system",
        role: "owner",
        active: true,
        password_configured: false,
      },
    },
  }));
});

const systemGraph = {
  nodes: [
    {
      id: "system-root",
      type: "SystemRoot",
      label: "Business AI Agents",
      summary: "Canonical system architecture",
      confidence: 1,
      source_count: 0,
      published: true,
      degree: 1,
      child_count: 1,
    },
    {
      id: "system-pillar",
      type: "SystemPillar",
      label: "Agent Architecture",
      summary: "System pillar",
      confidence: 1,
      source_count: 0,
      published: true,
      degree: 2,
      child_count: 1,
      primary_parent_id: "system-root",
    },
    {
      id: "system-concept",
      type: "Concept",
      label: "Orchestration",
      summary: "System concept",
      confidence: 1,
      source_count: 0,
      published: true,
      degree: 1,
      child_count: 0,
      primary_parent_id: "system-pillar",
    },
  ],
  edges: [
    {
      id: "system-root-pillar",
      source: "system-root",
      target: "system-pillar",
      type: "PARENT_OF",
      confidence: 1,
      evidence_count: 0,
      evidence: [],
    },
    {
      id: "system-pillar-concept",
      source: "system-pillar",
      target: "system-concept",
      type: "PARENT_OF",
      confidence: 1,
      evidence_count: 0,
      evidence: [],
    },
  ],
  meta: {
    node_count: 3,
    edge_count: 2,
    query: null,
    truncated: false,
    provider: "postgres-system",
    view: "hierarchy",
  },
};

test("Business AI Agents system map renders on its separate route", async ({ page }) => {
  await page.route("**/api/v1/graph/system?limit=1000", (route) =>
    route.fulfill({ json: systemGraph }),
  );

  await page.goto("/graph/system");

  await expect(page.getByRole("heading", { name: "Sơ đồ hệ thống Business AI Agents" })).toBeVisible();
  await expect(page.locator("a.back-link")).toHaveAttribute("href", "/graph");
  await expect(page.locator("main")).toHaveClass(/graph-page/);
  await expect(page.locator(".system-map-studio")).toBeVisible();
  await expect(page.getByText("GRAPH PROJECTION", { exact: true })).toHaveCount(0);
  await expect(page.getByText("The canonical system architecture is kept separate", { exact: false })).toHaveCount(0);
  await expect(page.getByTestId("node-details")).toHaveCount(0);
  await expect(page.getByRole("textbox", { name: "Tìm nút…" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Mạng" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Phân cấp" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: "Quỹ đạo" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Khám phá" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Nhãn" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: "Vừa khung" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sắp xếp lại" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Đặt lại" })).toBeVisible();
  await expect(page.getByTestId("graph-canvas")).toBeVisible();
  await expect(page.locator('.d3-node[data-node-id="system-root"]')).toBeVisible();
  await expect(page.locator(".d3-node")).toHaveCount(2);
  await expect(page.locator('.d3-system-label-overlay[data-node-id="system-root"] .d3-hierarchy-type'))
    .toHaveText("GỐC HỆ THỐNG");
  await expect(page.locator('.d3-system-label-overlay[data-node-id="system-pillar"] .d3-hierarchy-type'))
    .toHaveText("TRỤ CỘT HỆ THỐNG");
  await expect(page.locator(".d3-system-label-overlay .d3-hierarchy-type").filter({ hasText: "BOARD" })).toHaveCount(0);
  const foregroundLayer = await page.evaluate(() => {
    const graph = document.querySelector<SVGGElement>(".d3-graph-container")!;
    const nodes = graph.querySelector<SVGGElement>(".d3-nodes")!;
    const labels = graph.querySelector<SVGGElement>(".d3-labels")!;
    const children = [...graph.children];
    const overlay = labels.querySelector<SVGGElement>(".d3-system-label-overlay")!;
    const text = overlay.querySelector<SVGTextElement>(".d3-node-label")!;
    const source = nodes.querySelector<SVGTextElement>(".d3-node .d3-node-label")!;
    const style = getComputedStyle(text);
    return {
      afterNodes: children.indexOf(labels) > children.indexOf(nodes),
      overlayCount: labels.querySelectorAll(".d3-system-label-overlay").length,
      paintOrder: style.paintOrder,
      pointerEvents: getComputedStyle(overlay).pointerEvents,
      sourceVisibility: source.getAttribute("visibility"),
      strokeWidth: Number.parseFloat(style.strokeWidth),
      mainWidth: document.querySelector("main")!.getBoundingClientRect().width,
      canvasWidth: document.querySelector<HTMLElement>('[data-testid="graph-canvas"]')!
        .getBoundingClientRect().width,
      // Cột nội dung cạnh thanh điều hướng cố định: đồ thị phải chiếm gần hết cột này.
      contentWidth: document.querySelector<HTMLElement>("div.main")!.getBoundingClientRect().width,
      overflow: document.documentElement.scrollWidth - window.innerWidth,
    };
  });
  expect(foregroundLayer.afterNodes).toBe(true);
  expect(foregroundLayer.overlayCount).toBe(2);
  expect(foregroundLayer.paintOrder).toContain("stroke");
  expect(foregroundLayer.pointerEvents).toBe("none");
  expect(foregroundLayer.sourceVisibility).toBe("hidden");
  expect(foregroundLayer.strokeWidth).toBeGreaterThanOrEqual(2.5);
  expect(foregroundLayer.mainWidth / foregroundLayer.contentWidth).toBeGreaterThanOrEqual(0.9);
  expect(foregroundLayer.canvasWidth / foregroundLayer.contentWidth).toBeGreaterThanOrEqual(0.9);
  expect(foregroundLayer.overflow).toBeLessThanOrEqual(1);

  await page.locator('.d3-node[data-node-id="system-pillar"]').dispatchEvent("click");
  await expect(page.locator(".d3-node")).toHaveCount(3);
  await expect(page.locator('.d3-node[data-node-id="system-pillar"]'))
    .toHaveClass(/d3-hierarchy-board-expanded/);
  await expect(page.getByTestId("node-details")).toContainText("Trụ cột hệ thống");
  await expect(page.locator('.d3-system-label-overlay[data-node-id="system-concept"] .d3-hierarchy-type'))
    .toHaveText("KHÁI NIỆM");
  await expect(page.locator(".d3-system-label-overlay")).toHaveCount(3);
  const containment = await page.evaluate(() => {
    const board = document.querySelector<SVGGraphicsElement>(
      '.d3-node[data-node-id="system-pillar"] .d3-hierarchy-card',
    )?.getBoundingClientRect();
    const child = document.querySelector<SVGGraphicsElement>(
      '.d3-node[data-node-id="system-concept"] .d3-hierarchy-card',
    )?.getBoundingClientRect();
    if (!board || !child) return false;
    return child.left >= board.left && child.right <= board.right &&
      child.top >= board.top && child.bottom <= board.bottom;
  });
  expect(containment).toBe(true);

  await page.locator('.d3-node[data-node-id="system-pillar"]').dispatchEvent("click");
  await expect(page.locator(".d3-node")).toHaveCount(2);
  await expect(page.locator('.d3-node[data-node-id="system-concept"]')).toHaveCount(0);

  await page.getByRole("button", { name: "Mạng" }).click();
  await expect(page.getByRole("button", { name: "Mạng" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".d3-node")).toHaveCount(3);
  await page.getByRole("button", { name: "Quỹ đạo" }).click();
  await expect(page.getByRole("button", { name: "Quỹ đạo" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".d3-node")).toHaveCount(3);
  await page.getByRole("button", { name: "Phân cấp" }).click();
  await expect(page.locator(".d3-node")).toHaveCount(2);
  await page.getByRole("button", { name: "Khám phá" }).click();
  await expect(page.getByRole("button", { name: "Khám phá" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".graph-legend")).toBeVisible();
  await page.getByRole("button", { name: "Nhãn" }).click();
  await expect(page.getByRole("button", { name: "Nhãn" })).toHaveAttribute("aria-pressed", "false");
  await page.getByRole("button", { name: "Đặt lại" }).click();
  await expect(page.getByRole("button", { name: "Phân cấp" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: "Nhãn" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: "Khám phá" })).toHaveAttribute("aria-pressed", "false");
});
