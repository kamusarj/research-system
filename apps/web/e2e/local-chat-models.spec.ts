import { expect, test } from "@playwright/test";

for (const provider of ["ollama", "local_openai"]) {
  test(`${provider} chooses and checks an installed model, then reopens the pinned keyless session`, async ({ page }) => {
    let session: Record<string, unknown> | null = null;
    const messages: Record<string, unknown>[] = [];
    const mutations: Record<string, unknown>[] = [];
    const directModelRequests: string[] = [];
    let inventoryCalls = 0;
    let verificationCalls = 0;
    let changedDefault = false;
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (["11434", "11435", "1234"].includes(url.port)) directModelRequests.push(url.origin);
    });
    await page.route("**/api/v1/auth/config", (route) => route.fulfill({
      json: { enabled: false, mode: "disabled", csrf_cookie_name: "research_csrf" },
    }));
    await page.route("**/api/v1/auth/me", (route) => route.fulfill({
      json: { enabled: false, user: { id: "local-fixture", name: "Người dùng kiểm thử", role: "owner", active: true } },
    }));
    await page.route("**/api/v1/ai/providers", (route) => route.fulfill({
      json: [
        { id: "ollama", configured: true, model: changedDefault ? "different-default" : "operator-default" },
        { id: "local_openai", configured: true, model: "" },
      ],
    }));
    await page.route("**/api/v1/chat/connections/local/models", (route) => {
      expect(route.request().method()).toBe("POST");
      expect(route.request().postDataJSON()).toEqual({ provider });
      inventoryCalls++;
      return route.fulfill({ json: { provider, models: ["installed-a", "installed-b"] } });
    });
    await page.route("**/api/v1/chat/connections/local/verify", (route) => {
      expect(route.request().postDataJSON()).toEqual({ provider, model_name: "installed-b" });
      verificationCalls++;
      return route.fulfill({ json: { provider, model_name: "installed-b", verified: true } });
    });
    await page.route("**/api/v1/chat/sessions", (route) => {
      if (route.request().method() === "POST") {
        const body = route.request().postDataJSON();
        mutations.push(body);
        expect(body).toEqual({ scope_type: "graph", provider, credential_source: "system", model_name: "installed-b" });
        session = {
          id: "local-model-session", title: "Trò chuyện bằng mô hình cục bộ", scope_type: "graph",
          provider_name: provider, credential_source: "system", model_name: body.model_name,
          status: "active", source_type: "local", message_count: 0,
          created_at: "2026-11-18T00:00:00Z", updated_at: "2026-11-18T00:00:00Z",
        };
        return route.fulfill({ status: 201, json: session });
      }
      return route.fulfill({ json: { items: session ? [session] : [], total: session ? 1 : 0 } });
    });
    await page.route("**/api/v1/chat/sessions/local-model-session/messages", (route) => {
      if (route.request().method() === "POST") {
        const body = route.request().postDataJSON();
        mutations.push(body);
        expect(body).toEqual({ content: "Cùng phân tích ý tưởng này." });
        const user = { id: `user-${messages.length}`, role: "user", content: body.content, media: [], created_at: "2026-11-18T00:01:00Z" };
        const assistant = { ...user, id: `assistant-${messages.length}`, role: "assistant", content: "Đây là phản hồi từ mô hình đã chọn." };
        messages.push(user, assistant);
        return route.fulfill({ json: { session, user_message: user, assistant_message: assistant, change_set_id: null } });
      }
      return route.fulfill({ json: messages });
    });

    await page.goto("/chat");
    await page.getByRole("button", { name: "Cuộc trò chuyện mới", exact: true }).click();
    await page.getByLabel("Nhà cung cấp AI", { exact: true }).selectOption(provider);
    const create = page.getByRole("button", { name: "Tạo cuộc trò chuyện", exact: true });
    await expect(create).toBeDisabled();
    await expect(page.getByLabel("API key cá nhân", { exact: true })).toHaveCount(0);
    expect(inventoryCalls).toBe(0);
    expect(verificationCalls).toBe(0);
    await page.getByRole("button", { name: "Tải danh sách mô hình cục bộ" }).click();
    await page.getByLabel("Mô hình cục bộ", { exact: true }).selectOption("installed-b");
    await expect(create).toBeDisabled();
    expect(verificationCalls).toBe(0);
    await page.getByRole("button", { name: "Kiểm tra mô hình cục bộ", exact: true }).click();
    await expect(create).toBeEnabled();
    expect(mutations).toHaveLength(0);
    await create.click();
    await expect(page.getByText("Mô hình cố định · installed-b", { exact: true })).toBeVisible();
    await page.getByLabel("Tin nhắn", { exact: true }).fill("Cùng phân tích ý tưởng này.");
    await page.getByRole("button", { name: "Gửi", exact: true }).click();
    await expect(page.getByText("Đây là phản hồi từ mô hình đã chọn.", { exact: true })).toBeVisible();
    changedDefault = true;
    await page.reload();
    await expect(page.getByText("Mô hình cố định · installed-b", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Tin nhắn", { exact: true })).toBeEnabled();
    expect(inventoryCalls).toBe(1);
    expect(verificationCalls).toBe(1);
    expect(mutations).toHaveLength(2);
    expect(directModelRequests).toEqual([]);
    const storage = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }));
    expect(storage).not.toContain("installed-b");
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
  });
}
