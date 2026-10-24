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

test("reviewer can accept, approve and apply a governed graph change", async ({ page }) => {
  let lifecycleStatus = "needs_review";
  let reviewDecision = "pending";
  const changeSet = () => ({
    id: "change-set-1",
    origin_type: "document_workspace",
    origin_id: "workspace-1",
    title: "Map Agent Memory paper",
    summary: "Review ontology proposals before canonical publication.",
    lifecycle_status: lifecycleStatus,
    validation_summary: { valid_count: 1, warning_count: 1, error_count: 0 },
    created_by: "system",
    approved_by: lifecycleStatus === "approved" ? "reviewer" : null,
    applied_at: lifecycleStatus === "applied" ? "2026-07-18T05:00:00Z" : null,
    mutations: [{
      id: "mutation-1",
      mutation_order: 0,
      operation: "CREATE_NODE",
      target_kind: "knowledge_node",
      target_id: "new-node-1",
      before_json: {},
      proposed_json: {
        canonical_label: "Agent Memories",
        node_type: "Concept",
        primary_parent_id: "parent-1",
        candidates: [{
          node_id: "canonical-1",
          canonical_label: "Agent Memory",
          node_type: "Concept",
          primary_parent_id: "parent-1",
          matched_by: "similarity",
          score: 0.92,
        }],
      },
      validation_status: "warning",
      validation_messages: [{
        level: "warning",
        code: "SIMILAR_CANDIDATE",
        message: "Review this candidate before creating a node.",
      }],
      review_decision: reviewDecision,
      reviewed_by: reviewDecision === "accepted" ? "reviewer" : null,
      created_at: "2026-07-18T00:00:00Z",
      updated_at: "2026-07-18T00:00:00Z",
    }],
    created_at: "2026-07-18T00:00:00Z",
    updated_at: "2026-07-18T00:00:00Z",
  });

  await page.route("**/api/v1/graph/change-sets/change-set-1**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (route.request().method() === "POST") {
      if (path.endsWith("/decision")) reviewDecision = "accepted";
      if (path.endsWith("/approve")) lifecycleStatus = "approved";
      if (path.endsWith("/apply")) lifecycleStatus = "applied";
    }
    await route.fulfill({ json: changeSet() });
  });

  await page.goto("/graph/changes/change-set-1");
  const candidates = page.locator(".candidate-comparison");
  await expect(candidates).toContainText("Agent Memory");
  await expect(candidates).toContainText("92%");
  await page.getByRole("button", { name: "Chấp nhận thay đổi" }).click();
  await expect(page.getByText("đã chấp nhận", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Duyệt thay đổi hợp lệ" }).click();
  await page.getByRole("button", { name: "Áp dụng vào đồ thị" }).click();
  await expect(page.getByRole("button", { name: "Tạo bộ thay đổi bù" })).toBeVisible();

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
});
