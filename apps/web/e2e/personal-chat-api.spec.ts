import { expect, test } from "@playwright/test";

test("personal API works without a system key and requires re-entry after reload", async ({ page }, testInfo) => {
  const syntheticKey = "synthetic-e2e-personal-key";
  let session: Record<string, unknown> | null = null;
  const messages: Record<string, unknown>[] = [];
  const requests: Record<string, unknown>[] = [];
  await page.route("**/api/v1/auth/config", (route) => route.fulfill({ json: { enabled: false, mode: "disabled", csrf_cookie_name: "research_csrf" } }));
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: { enabled: false, user: { id: "test-user", name: "Người dùng kiểm thử", role: "owner", active: true } } }));
  await page.route("**/api/v1/ai/providers", (route) => route.fulfill({ json: [
    { id: "openai", configured: false, model: "test-openai-model" },
    { id: "deepseek", configured: false, model: "test-deepseek-model" },
  ] }));
  await page.route("**/api/v1/chat/connections/models", async (route) => {
    expect(route.request().postDataJSON()).toEqual({ provider: "deepseek", personal_api_key: syntheticKey });
    await route.fulfill({ json: { provider: "deepseek", models: ["personal-model", "another-model"] } });
  });
  await page.route("**/api/v1/chat/connections/verify", async (route) => {
    expect(route.request().postDataJSON()).toEqual({ provider: "deepseek", personal_api_key: syntheticKey, model_name: "personal-model" });
    await route.fulfill({ json: { provider: "deepseek", model_name: "personal-model", verified: true } });
  });
  await page.route("**/api/v1/chat/sessions", async (route) => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON();
      requests.push(body);
      expect(body.personal_api_key).toBe(syntheticKey);
      expect(body.credential_source).toBe("personal");
      session = { id: "personal-session", title: "Nghiên cứu với API riêng", scope_type: "graph", provider_name: body.provider,
        credential_source: "personal", model_name: body.model_name, status: "active", source_type: "local",
        message_count: 0, created_at: "2026-09-05T07:00:00Z", updated_at: "2026-09-05T07:00:00Z" };
      await route.fulfill({ status: 201, json: session });
    } else await route.fulfill({ json: { items: session ? [session] : [], total: session ? 1 : 0 } });
  });
  await page.route("**/api/v1/chat/sessions/personal-session/messages", async (route) => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON();
      requests.push(body);
      expect(body.personal_api_key).toBe(syntheticKey);
      const user = { id: "user-1", role: "user", content: body.content, media: [], created_at: "2026-09-05T07:01:00Z" };
      const assistant = { ...user, id: "assistant-1", role: "assistant", content: "Đây là câu trả lời qua API cá nhân." };
      messages.push(user, assistant);
      await route.fulfill({ json: { session, user_message: user, assistant_message: assistant } });
    } else await route.fulfill({ json: messages });
  });

  await page.goto("/chat");
  await page.getByRole("button", { name: "API của tôi", exact: true }).click();
  await expect(page.getByLabel("API key cá nhân", { exact: true })).toHaveAttribute("type", "password");
  await page.getByLabel("Nhà cung cấp API").selectOption("deepseek");
  await page.getByLabel("API key cá nhân", { exact: true }).fill(syntheticKey);
  await page.getByRole("button", { name: "Tải danh sách mô hình" }).click();
  await page.getByLabel("Mô hình AI").selectOption("personal-model");
  await page.screenshot({ path: `/tmp/personal-chat-settings-${testInfo.project.name}.png`, animations: "disabled" });
  await page.getByRole("button", { name: "Kiểm tra và kết nối" }).click();
  expect(requests).toHaveLength(0);
  await page.getByRole("button", { name: "Tạo cuộc trò chuyện", exact: true }).click();
  await expect(page.getByText("API cá nhân · personal-model")).toBeVisible();
  await page.getByLabel("Tin nhắn", { exact: true }).fill("Phân tích ý tưởng này.");
  await page.getByRole("button", { name: "Gửi", exact: true }).click();
  await expect(page.getByText("Đây là câu trả lời qua API cá nhân.")).toBeVisible();
  expect(requests).toHaveLength(2);
  const browserStorage = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }));
  expect(browserStorage).not.toContain(syntheticKey);
  await page.reload();
  await expect(page.getByLabel("Tin nhắn", { exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Nhập lại API key", exact: true }).click();
  await expect(page.getByLabel("API key cá nhân", { exact: true })).toHaveValue("");
  expect(requests).toHaveLength(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
});
