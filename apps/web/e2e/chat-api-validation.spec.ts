import { expect, test } from "@playwright/test";

test("explains invalid key, credit, model and rate errors before allowing a connection", async ({ page }, testInfo) => {
  await page.route("**/api/v1/auth/config", (route) => route.fulfill({ json: { enabled: false, mode: "disabled", csrf_cookie_name: "research_csrf" } }));
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ json: { enabled: false, user: { id: "test-user", name: "Kiểm thử", role: "owner", active: true } } }));
  await page.route("**/api/v1/ai/providers", (route) => route.fulfill({ json: [{ id: "openai", configured: false, model: "model-test" }] }));
  await page.route("**/api/v1/chat/sessions", (route) => route.fulfill({ json: { items: [], total: 0 } }));
  let modelLoads = 0;
  await page.route("**/api/v1/chat/connections/models", (route) => {
    modelLoads++;
    return modelLoads === 1 ? route.fulfill({ status: 422, json: { error: { code: "CHAT_API_KEY_INVALID" } } })
      : route.fulfill({ json: { provider: "openai", models: ["model-a", "model-b"] } });
  });
  let verifyCount = 0;
  const failures = ["CHAT_CREDIT_EXHAUSTED", "CHAT_QUOTA_EXCEEDED", "CHAT_MODEL_UNAVAILABLE", "CHAT_MODEL_INCOMPATIBLE", "CHAT_PROVIDER_RATE_LIMITED"];
  await page.route("**/api/v1/chat/connections/verify", (route) => {
    const code = failures[verifyCount++];
    const body = route.request().postDataJSON();
    return code ? route.fulfill({ status: code.includes("RATE") ? 429 : 422, json: { error: { code, message: "unsafe-upstream-text" } } })
      : route.fulfill({ json: { provider: body.provider, model_name: body.model_name, verified: true } });
  });
  await page.goto("/chat");
  await page.getByRole("button", { name: "API của tôi", exact: true }).click();
  const connectionAlert = page.locator(".chat-api-settings").getByRole("alert");
  await page.getByLabel("API key cá nhân", { exact: true }).fill("synthetic-wrong-key");
  await page.getByRole("button", { name: "Tải danh sách mô hình" }).click();
  await expect(connectionAlert).toContainText("Không xác thực được API key");
  await expect(page.getByRole("button", { name: "Kiểm tra và kết nối" })).toBeDisabled();
  await page.getByLabel("API key cá nhân", { exact: true }).fill("synthetic-new-key");
  await page.getByRole("button", { name: "Tải danh sách mô hình" }).click();
  await page.getByLabel("Mô hình AI").selectOption("model-b");
  expect(verifyCount).toBe(0);
  const messages = ["hết credit", "không còn hạn mức", "chưa được cấp quyền", "không hỗ trợ cấu hình chat", "giới hạn tốc độ"];
  for (const message of messages) {
    await page.getByRole("button", { name: "Kiểm tra và kết nối" }).click();
    await expect(connectionAlert).toContainText(message);
    await expect(page.getByText("Kết nối API của bạn", { exact: true })).toBeVisible();
    await expect(page.getByText("unsafe-upstream-text")).toHaveCount(0);
  }
  await connectionAlert.scrollIntoViewIfNeeded();
  await page.screenshot({ path: `/tmp/chat-api-validation-${testInfo.project.name}.png`, animations: "disabled" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
  await page.getByRole("button", { name: "Kiểm tra và kết nối" }).click();
  await expect(page.getByLabel("Nguồn API")).toHaveValue("personal");
  expect(verifyCount).toBe(6);
});
