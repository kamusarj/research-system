import { expect, test } from "@playwright/test";
import type { ChatMessage, ChatSession } from "../lib/types";

test("bounded initial chat history can reveal every older message", async ({ page }) => {
  await page.route("**/api/v1/auth/config", (route) => route.fulfill({
    json: { enabled: false, mode: "disabled", csrf_cookie_name: "research_csrf" },
  }));
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({
    json: { enabled: false, user: { id: "local-user", name: "Fixture", role: "owner", active: true } },
  }));
  const session: ChatSession = {
    id: "history-fixture", title: "Window fixture", scope_type: "graph", scope_id: null,
    provider_name: "codex", model_name: "fixture", conversation_summary: "", status: "active",
    prompt_version: "fixture", source_type: "local", source_url: null, source_snapshot_hash: null,
    source_imported_at: null, imported_message_count: 0, message_count: 24,
    created_at: "2026-11-03T00:00:00Z", updated_at: "2026-11-03T00:00:00Z",
  };
  const messages: ChatMessage[] = Array.from({ length: 24 }, (_, index) => ({
    id: `message-${index + 1}`, session_id: session.id, role: "assistant", content: `History fixture ${index + 1}`,
    provider_response_id: null, provider_request_id: null, tool_calls: [], tool_results: [],
    linked_change_set_id: null, usage: {}, latency_ms: 0, error_code: null, origin_type: "local", media: [],
    created_at: "2026-11-03T00:00:00Z",
  }));
  await page.route("**/api/v1/ai/providers", (route) => route.fulfill({
    json: [{ id: "codex", configured: true, reachable: true, model: "fixture" }],
  }));
  await page.route("**/api/v1/chat/sessions", (route) => route.fulfill({ json: { items: [session], total: 1 } }));
  await page.route("**/api/v1/chat/sessions/history-fixture/messages", (route) => route.fulfill({ json: messages }));
  const historyLoaded = page.waitForResponse((response) =>
    response.url().endsWith("/chat/sessions/history-fixture/messages") && response.status() === 200);
  await page.goto("/chat");
  await historyLoaded;
  await expect(page.getByText("History fixture 24", { exact: true })).toBeVisible();
  await expect(page.getByText("History fixture 1", { exact: true })).toHaveCount(0);
  const older = page.getByRole("button", { name: /tin nhắn cũ hơn/ });
  for (let index = 0; index < 2; index += 1) await older.click();
  await expect(page.getByText("History fixture 1", { exact: true })).toHaveCount(1);
  await expect(page.locator("[data-chat-message-id]")).toHaveCount(24);
  await expect(older).toHaveCount(0);
});
