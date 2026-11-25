import { chromium } from "@playwright/test";

const BASE = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const OUT = process.env.SCREENSHOT_DIR ?? "/tmp/opencode/weave-shots";

const layoutGraph = (view: string) => ({
  nodes: [
    { id: "concept:memory", type: "Concept", label: "Agent memory", summary: "Memory patterns used by business agents.", confidence: 1, source_count: 3, published: true, degree: 4, child_count: 3, lifecycle_status: "approved", provenance: { created_by_type: "reviewer" } },
    { id: "research:grounding", type: "ResearchItem", label: "Evidence-grounded agent memory architectures", summary: "Research.", confidence: 0.96, source_count: 1, published: true, degree: 1, primary_parent_id: "concept:memory", child_count: 0, lifecycle_status: "approved", provenance: { created_by_type: "reviewer" } },
    { id: "concept:approval", type: "Concept", label: "Human approval improves reliability của hệ thống", summary: "Approval workflows.", confidence: 0.9, source_count: 2, published: true, degree: 2, primary_parent_id: "concept:memory", child_count: 0, lifecycle_status: "approved", provenance: { created_by_type: "reviewer" } },
    { id: "tech:pgvector", type: "Technology", label: "pgvector semantic search", summary: "Vector search.", confidence: 0.92, source_count: 2, published: true, degree: 3, primary_parent_id: "concept:memory", child_count: 0, lifecycle_status: "approved", provenance: { created_by_type: "reviewer" } },
    { id: "article:weave", type: "Article", label: "Node-based canvas interaction patterns", summary: "Article.", confidence: 0.8, source_count: 1, published: true, degree: 1, child_count: 0, lifecycle_status: "approved", provenance: { created_by_type: "reviewer" } },
  ],
  edges: [
    { id: "e1", source: "concept:memory", target: "research:grounding", type: "PARENT_OF", confidence: 1, evidence_count: 0, evidence: [] },
    { id: "e2", source: "concept:memory", target: "concept:approval", type: "PARENT_OF", confidence: 1, evidence_count: 0, evidence: [] },
    { id: "e3", source: "concept:memory", target: "tech:pgvector", type: "PARENT_OF", confidence: 1, evidence_count: 0, evidence: [] },
    { id: "e4", source: "research:grounding", target: "concept:approval", type: "SUPPORTS", confidence: 0.9, evidence_count: 1, evidence: [] },
    { id: "e5", source: "tech:pgvector", target: "article:weave", type: "USES_TECH", confidence: 0.85, evidence_count: 1, evidence: [] },
    { id: "e6", source: "article:weave", target: "concept:memory", type: "RELATED_TO", confidence: 0.7, evidence_count: 0, evidence: [] },
  ],
  meta: { node_count: 5, edge_count: 6, total_node_count: 5, total_edge_count: 6, query: null, truncated: false, provider: "postgres", view },
});

const mockRoutes = async (page: import("@playwright/test").Page) => {
  await page.route("**/api/v1/auth/config", (route) => route.fulfill({ json: { enabled: false, mode: "local", csrf_cookie_name: "research_csrf" } }));
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: { enabled: false, user: { id: "u", name: "Owner", email: "o@r.s", role: "owner", active: true, password_configured: false } } }));
  await page.route("**/api/v1/graph**", (route) => {
    const url = new URL(route.request().url());
    return route.fulfill({ json: layoutGraph(url.searchParams.get("view") ?? "hierarchy") });
  });
};

const run = async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  for (const theme of ["light", "dark"] as const) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await context.addInitScript((value) => window.localStorage.setItem("research-theme", value), theme);
    const page = await context.newPage();
    await mockRoutes(page);
    await page.goto(`${BASE}/graph`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1600);
    await page.screenshot({ path: `${OUT}/graph-hierarchy-${theme}.png` });
    await page.getByRole("button", { name: "Mạng" }).click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: `${OUT}/graph-relationship-${theme}.png` });
    await page.getByRole("button", { name: "Quỹ đạo" }).click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: `${OUT}/graph-orbit-${theme}.png` });
    await context.close();
  }
  await browser.close();
  console.log("screenshots saved to", OUT);
};

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
