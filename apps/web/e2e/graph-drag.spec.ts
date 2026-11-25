import { expect, test } from "@playwright/test";

/**
 * Free-drag contract (Weave-style): the grabbed card tracks the pointer 1:1, incident
 * wires follow live, the placement survives, and "Sắp xếp lại" releases it again.
 */

const dragGraph = {
  nodes: [
    {
      id: "concept:memory",
      type: "Concept",
      label: "Agent memory",
      summary: "Memory patterns used by business agents.",
      confidence: 1,
      source_count: 3,
      published: true,
      degree: 3,
      child_count: 0,
      lifecycle_status: "approved",
      provenance: { created_by_type: "reviewer" },
    },
    {
      id: "concept:approval",
      type: "Concept",
      label: "Human approval",
      summary: "Approval workflows.",
      confidence: 0.9,
      source_count: 2,
      published: true,
      degree: 1,
      child_count: 0,
      lifecycle_status: "approved",
      provenance: { created_by_type: "reviewer" },
    },
    {
      id: "tech:pgvector",
      type: "Technology",
      label: "pgvector semantic search",
      summary: "Vector search.",
      confidence: 0.92,
      source_count: 2,
      published: true,
      degree: 1,
      child_count: 0,
      lifecycle_status: "approved",
      provenance: { created_by_type: "reviewer" },
    },
  ],
  edges: [
    {
      id: "edge:memory-approval",
      source: "concept:memory",
      target: "concept:approval",
      type: "RELATED_TO",
      confidence: 0.9,
      evidence_count: 0,
      evidence: [],
    },
    {
      id: "edge:memory-pgvector",
      source: "concept:memory",
      target: "tech:pgvector",
      type: "USES_TECH",
      confidence: 0.9,
      evidence_count: 0,
      evidence: [],
    },
  ],
  meta: {
    node_count: 3,
    edge_count: 2,
    total_node_count: 3,
    total_edge_count: 2,
    query: null,
    truncated: false,
    provider: "postgres",
    view: "relationship",
  },
};

const parseTranslate = (transform: string | null) => {
  const match = /translate\(([-\d.]+)[, ]+([-\d.]+)\)/.exec(transform ?? "");
  return match ? { x: Number(match[1]), y: Number(match[2]) } : null;
};

test("free drag moves a node with its wires and keeps the placement until auto-arrange", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chrome", "interaction proof runs once on desktop");
  await page.setViewportSize({ width: 1440, height: 900 });
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
  await page.route("**/api/v1/graph**", (route) => route.fulfill({ json: dragGraph }));

  await page.goto("/graph", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Mạng" }).click();
  await expect(page.locator('.d3-node[data-node-id="concept:memory"] .d3-node-card')).toHaveCount(1);

  const node = page.locator('.d3-node[data-node-id="concept:memory"]');
  const before = parseTranslate(await node.getAttribute("transform"));
  expect(before).not.toBeNull();
  const edgeBefore = await page.locator(".d3-network-edge").first().getAttribute("d");

  const box = (await node.boundingBox())!;
  const startX = box.x + box.width / 2;
  const startY = box.y + box.height / 2;
  const deltaX = 180;
  const deltaY = 90;

  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(startX + deltaX / 2, startY + deltaY / 2, { steps: 6 });
  await expect(node).toHaveClass(/d3-node-dragging/);
  const midDrag = await node.getAttribute("transform");
  const labelToggle = page.getByRole("button", { name: "Nhãn", exact: true });
  await labelToggle.dispatchEvent("click");
  await expect(labelToggle).toHaveAttribute("aria-pressed", "false");
  await expect(node.locator(".d3-node-label")).toHaveCSS("opacity", "0");
  await expect(node).toHaveAttribute("transform", midDrag!);
  await expect(node).toHaveClass(/d3-node-dragging/);
  await page.mouse.move(startX + deltaX, startY + deltaY, { steps: 6 });
  await page.mouse.up();
  await expect(node).not.toHaveClass(/d3-node-dragging/);

  const after = parseTranslate(await node.getAttribute("transform"));
  expect(after).not.toBeNull();
  const scale = await page.evaluate(() => {
    const matrix = document.querySelector<SVGGElement>(".d3-graph-container")!
      .transform.baseVal.consolidate()!.matrix;
    return matrix.a;
  });
  expect(Math.abs((after!.x - before!.x) * scale - deltaX)).toBeLessThan(24);
  expect(Math.abs((after!.y - before!.y) * scale - deltaY)).toBeLessThan(24);

  const edgeAfterDrag = await page.locator(".d3-network-edge").first().getAttribute("d");
  expect(edgeAfterDrag).not.toBe(edgeBefore);

  // The placement survives idle time and hover churn.
  await page.locator(".graph-toolbar").hover();
  await page.waitForTimeout(250);
  expect(parseTranslate(await node.getAttribute("transform"))).toEqual(after);

  // Auto-arrange releases the pin and recomputes the layout.
  await page.getByRole("button", { name: "Sắp xếp lại" }).click();
  await expect.poll(async () => parseTranslate(await node.getAttribute("transform"))).not.toEqual(after);

  await page.getByRole("button", { name: "Quỹ đạo" }).click();
  const ring = page.locator(".d3-orbit-ring").first();
  const idleNode = page.locator('.d3-node[data-node-id="concept:approval"]');
  await expect(ring).toBeVisible();
  const centerBefore = await ring.getAttribute("cx");
  await idleNode.locator(".d3-node-card").click();
  await expect(page.getByTestId("node-details")).toContainText("Human approval");
  const idleBefore = await idleNode.getAttribute("transform");
  const orbitCard = node.locator(".d3-node-card");
  await orbitCard.hover();
  const orbitBox = (await orbitCard.boundingBox())!;
  const orbitX = orbitBox.x + orbitBox.width / 2;
  const orbitY = orbitBox.y + orbitBox.height / 2;
  await page.mouse.move(orbitX, orbitY);
  await page.mouse.down();
  await page.mouse.move(orbitX + 55, orbitY + 20, { steps: 6 });
  await expect(node).toHaveClass(/d3-node-dragging/);
  await page.mouse.up();
  const pinned = await node.getAttribute("transform");

  await page.setViewportSize({ width: 1080, height: 810 });
  await expect(ring).not.toHaveAttribute("cx", centerBefore!);
  await expect(idleNode).not.toHaveAttribute("transform", idleBefore!);
  await expect(node).toHaveAttribute("transform", pinned!);
  await page.getByRole("button", { name: "Sắp xếp lại" }).click();
  await expect(node).not.toHaveAttribute("transform", pinned!);
});
