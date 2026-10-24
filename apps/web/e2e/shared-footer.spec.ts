import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/auth/config") {
      await route.fulfill({ json: { enabled: false, mode: "disabled", csrf_cookie_name: "research_csrf" } });
      return;
    }
    if (path === "/api/v1/auth/me") {
      await route.fulfill({
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
      });
      return;
    }
    if (path === "/api/v1/research") {
      await route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 6 } });
      return;
    }
    if (path === "/api/v1/ingestion/links") {
      await route.fulfill({ json: [] });
      return;
    }
    await route.fulfill({ json: {} });
  });
});

test("shared footer stays minimal and responsive", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });

  const footer = page.getByRole("contentinfo");
  await footer.scrollIntoViewIfNeeded();
  await expect(footer).toBeVisible();
  await expect(footer.getByRole("link", { name: "Trang chủ Hệ thống nghiên cứu" })).toBeVisible();
  await expect(footer.locator("nav")).toHaveCount(1);
  await expect(footer.getByRole("link")).toHaveCount(4);

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "footer must not make the page scroll horizontally").toBeLessThanOrEqual(1);
});
