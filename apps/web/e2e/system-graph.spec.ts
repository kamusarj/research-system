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
  await page.route("**/api/v1/graph/system", (route) =>
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
  const rootOverlay = page.locator('.d3-system-label-overlay[data-node-id="system-root"]');
  const pillar = page.locator('.d3-node[data-node-id="system-pillar"]');
  await expect(rootOverlay.locator(".d3-node-label")).toHaveCSS("opacity", "0");
  await expect(rootOverlay.locator(".d3-hierarchy-type")).toHaveCSS("opacity", "0");
  await expect(pillar).toHaveAttribute("aria-label", /Agent Architecture/);
  await pillar.dispatchEvent("click");
  await expect(page.locator('.d3-node[data-node-id="system-concept"]')).toBeVisible();
  await expect(rootOverlay.locator(".d3-node-label")).toHaveCSS("opacity", "0");
  await page.getByRole("button", { name: "Đặt lại" }).click();
  await expect(page.getByRole("button", { name: "Phân cấp" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: "Nhãn" })).toHaveAttribute("aria-pressed", "true");
  await expect(rootOverlay.locator(".d3-node-label")).toHaveCSS("opacity", "1");
  await expect(page.getByRole("button", { name: "Khám phá" })).toHaveAttribute("aria-pressed", "false");
});

test("a system map drag keeps its card and camera when search changes the graph", async ({ page }, testInfo) => {
  await page.route("**/api/v1/graph/system", (route) =>
    route.fulfill({ json: systemGraph }),
  );
  await page.goto("/graph/system");
  await page.getByRole("button", { name: "Mạng", exact: true }).click();
  const node = page.locator('.d3-node[data-node-id="system-root"]');
  const card = node.locator(".d3-node-card");
  await card.scrollIntoViewIfNeeded();
  const box = (await card.boundingBox())!;
  const x = Math.round(box.x + box.width / 2);
  const y = Math.round(box.y + box.height / 2);
  const graph = page.locator(".d3-graph-container");
  const wire = page.locator('[data-edge-id="system-root-pillar"]');
  const before = await node.getAttribute("transform");
  const wireBefore = await wire.getAttribute("d");
  const camera = await graph.getAttribute("transform");

  const cdp = testInfo.project.name === "mobile-chrome" ? await page.context().newCDPSession(page) : null;
  const start = async () => {
    if (cdp) {
      await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y }] });
    } else {
      await page.mouse.move(x, y);
      await page.mouse.down();
    }
  };
  const move = async (offset: number) => {
    if (cdp) {
      await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x, y: y + offset }] });
    } else {
      await page.mouse.move(x, y + offset);
    }
  };

  if (cdp) {
    await start();
    await move(32);
    await expect(node).toHaveClass(/d3-node-dragging/);
    await cdp.send("Input.dispatchTouchEvent", { type: "touchCancel", touchPoints: [] });
    await expect(node).not.toHaveClass(/d3-node-dragging/);
    await expect(node).toHaveAttribute("transform", before!);
    await expect(wire).toHaveAttribute("d", wireBefore!);
  }

  await start();
  await expect(node).not.toHaveClass(/d3-node-dragging/);
  await move(32);
  await expect(node).toHaveClass(/d3-node-dragging/);
  const midDrag = await node.getAttribute("transform");
  await page.getByRole("textbox", { name: "Tìm nút…" }).evaluate((input) => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "Agent Architecture");
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await expect(page.locator(".graph-canvas-status")).toContainText("2 nút");
  await expect(graph).toHaveAttribute("transform", camera!);
  await expect(node).toHaveAttribute("transform", midDrag!);
  await move(65);
  await expect(node).not.toHaveAttribute("transform", midDrag!);
  const finalPosition = await node.getAttribute("transform");
  if (cdp) await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  else await page.mouse.up();

  await expect(node).not.toHaveClass(/d3-node-dragging/);
  await expect(page.locator('.d3-node[data-node-id="system-concept"]')).toHaveCount(0);
  await expect(node).toHaveAttribute("transform", finalPosition!);
  await expect(wire).not.toHaveAttribute("d", wireBefore!);
  await expect(graph).toHaveAttribute("transform", camera!);

  if (cdp) {
    const cardBox = (await card.boundingBox())!;
    const viewport = page.viewportSize()!;
    const cardX = Math.round(cardBox.x + cardBox.width / 2);
    const cardY = Math.round(cardBox.y + cardBox.height / 2);
    const direction = cardX < viewport.width / 2 ? 1 : -1;
    const finger = { x: cardX, y: cardY + 24, id: 0 };
    await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ ...finger, y: cardY }] });
    await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [finger] });
    await expect(node).toHaveClass(/d3-node-dragging/);
    const second = { x: cardX + direction * 46, y: finger.y, id: 1 };
    await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [finger, second] });
    await cdp.send("Input.dispatchTouchEvent", {
      type: "touchMove",
      touchPoints: [finger, { ...second, x: cardX + direction * 112 }],
    });
    await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await expect(graph).not.toHaveAttribute("transform", camera!);
    await expect(node).not.toHaveClass(/d3-node-dragging/);
    await expect(node).toHaveAttribute("transform", finalPosition!);
  }
});
