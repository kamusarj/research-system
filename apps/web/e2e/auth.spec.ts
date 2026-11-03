import { expect, test, type Page } from "@playwright/test";

const ownerEmail = process.env.E2E_OWNER_EMAIL;
const viewerEmail = process.env.E2E_VIEWER_EMAIL;
const password = process.env.E2E_AUTH_PASSWORD;

async function signIn(page: Page, email: string) {
  await page.goto("/research");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mật khẩu").fill(password!);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page.getByRole("heading", { name: "Thư viện nghiên cứu" })).toBeVisible();
}

test.describe("authenticated role experience", () => {
  test.skip(!ownerEmail || !viewerEmail || !password, "enabled-auth runtime credentials are required");

  test("owner can enter the workspace and revoke the browser session", async ({ page }) => {
    await signIn(page, ownerEmail!);
    await expect(page.getByRole("button", { name: "Nghiên cứu mới" })).toBeVisible();
    await page.getByRole("button", { name: "Đăng xuất" }).click();
    await expect(page.getByRole("heading", { name: "Đăng nhập" })).toBeVisible();
  });

  test("viewer can read but mutation controls stay hidden", async ({ page }) => {
    await signIn(page, viewerEmail!);
    await page.goto("/ingestion");
    await expect(page.getByRole("heading", { name: "Nhập và duyệt liên kết" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Xử lý nguồn" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Thêm nguồn" })).toHaveCount(0);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
});

test.describe("authenticated server chat history", () => {
  test.use({ timezoneId: "Pacific/Honolulu" });
  test.skip(!ownerEmail || !password || !process.env.E2E_CHAT_HISTORY,
    "requires a disposable database with the 24-message SSR history fixture");

  test("hydrates across time zones and fetches older messages on demand", async ({ page }) => {
    await signIn(page, ownerEmail!);
    const failures: string[] = [];
    const messageRequests: string[] = [];
    page.on("pageerror", (error) => failures.push(error.name));
    page.on("request", (request) => {
      if (/\/chat\/sessions\/[^/]+\/messages$/.test(request.url())) messageRequests.push(request.method());
    });
    await page.goto("/chat");
    await expect(page.getByText("SSR history fixture 24", { exact: true })).toBeVisible();
    await expect(page.locator("[data-chat-message-id]")).toHaveCount(8);
    await page.waitForLoadState("networkidle");
    expect(messageRequests).toHaveLength(0);
    await expect(page.locator("[data-chat-message-id] time").first()).toHaveText("14:00");
    const older = page.getByRole("button", { name: /tin nhắn cũ hơn/ });
    await older.click();
    await expect(page.locator("[data-chat-message-id]")).toHaveCount(16);
    expect(messageRequests).toEqual(["GET"]);
    await older.click();
    await expect(page.locator("[data-chat-message-id]")).toHaveCount(24);
    await expect(older).toHaveCount(0);
    expect(messageRequests).toEqual(["GET"]);
    expect(failures).toEqual([]);
  });
});
