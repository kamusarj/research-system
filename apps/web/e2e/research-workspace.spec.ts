import { expect, test, type Page } from "@playwright/test";

function observeRuntimeFailures(page: Page) {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") failures.push(`console: ${message.text()}`);
  });
  page.on("response", (response) => {
    if (response.url().includes("/api/v1/") && response.status() >= 500) {
      failures.push(`api: ${response.status()} ${response.url()}`);
    }
  });
  return failures;
}

test("primary workspaces hydrate without console or API failures", async ({ page }) => {
  const failures = observeRuntimeFailures(page);
  for (const route of ["/", "/ingestion", "/documents", "/research", "/graph", "/graph/changes", "/chat", "/search", "/gaps", "/collector"]) {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    await expect(page.locator("main")).toBeVisible();
    const badgeLabels = await page.locator(".badge").allTextContents();
    expect(badgeLabels.filter((label) => label.startsWith("status."))).toEqual([]);
  }
  expect(failures).toEqual([]);
});

test("workspace uses the research desk visual language", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("banner")).toBeVisible();
  await expect(page.locator(".brand-name")).toContainText("Hệ thống nghiên cứu");
  await expect(page.locator(".dash-hero")).toBeVisible();
  const footer = page.getByRole("contentinfo");
  await expect(footer).toBeVisible();
  await expect(footer.getByRole("link", { name: "Trang chủ Hệ thống nghiên cứu" })).toBeVisible();
  await expect(footer.locator("nav")).toHaveCount(1);
  const visualTokens = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement);
    const action = getComputedStyle(document.querySelector(".primary-link")!);
    const footer = getComputedStyle(document.querySelector(".site-footer")!);
    return {
      background: root.getPropertyValue("--bg").trim(),
      primary: root.getPropertyValue("--primary").trim(),
      actionBackground: action.backgroundColor,
      actionRadius: action.borderRadius,
      footerBackground: footer.backgroundColor,
      hasWorkspaceBar: Boolean(document.querySelector(".workspace-bar")),
      navigationDirection: getComputedStyle(document.querySelector(".topnav")!).flexDirection,
    };
  });
  expect({ ...visualTokens, navigationDirection: undefined }).toEqual({
    background: "#f1f5f3",
    primary: "#087a70",
    actionBackground: "rgb(157, 232, 221)",
    actionRadius: "10px",
    footerBackground: "rgb(8, 32, 41)",
    hasWorkspaceBar: true,
    navigationDirection: undefined,
  });
  expect(visualTokens.navigationDirection).toBe((page.viewportSize()?.width ?? 0) > 1180 ? "column" : "row");
});

test("multi-source intake detects and submits links independently", async ({ page }) => {
  const failures = observeRuntimeFailures(page);
  await page.goto("/ingestion");
  await page.getByLabel("URL công khai").fill(
    "https://github.com/octocat/Hello-World\nhttps://arxiv.org/abs/1706.03762",
  );
  const provider = page.getByLabel("Nhà cung cấp AI");
  await expect(provider).not.toHaveValue("");
  expect(await provider.inputValue()).not.toBe("mock");
  await expect(provider.locator('option[value="mock"]')).toHaveCount(0);
  await expect(page.getByText("GitHub", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Bài báo khoa học", { exact: true }).first()).toBeVisible();
  const responses = Promise.all([
    page.waitForResponse((response) => response.url().endsWith("/api/v1/ingestion/links") && response.request().method() === "POST"),
    page.waitForResponse((response) => response.url().endsWith("/api/v1/ingestion/links") && response.request().method() === "POST"),
  ]);
  await page.getByRole("button", { name: "Xử lý nguồn" }).click();
  await responses;
  await expect(page.getByText("octocat/Hello-World", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Attention Is All You Need", { exact: true }).first()).toBeVisible();
  expect(failures).toEqual([]);
});

test("responsive layout has no horizontal page overflow", async ({ page }) => {
  await page.goto("/ingestion");
  await page.waitForLoadState("networkidle");
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
});

test("document authoring draft survives refresh and reopening without a discard action", async ({ page }) => {
  await page.goto("/documents");
  const title = page.getByLabel("Tiêu đề tài liệu");
  const content = page.getByLabel("Nội dung tài liệu");
  await expect(title).toBeVisible();

  await title.fill("Refresh-safe agent notes");
  await content.fill("# Agent notes\n\nKeep this text after F5.");
  await expect(page.getByText("Đã lưu trong trình duyệt này")).toBeVisible();

  await page.reload();
  await expect(page.getByLabel("Tiêu đề tài liệu")).toHaveValue("Refresh-safe agent notes");
  await expect(page.getByLabel("Nội dung tài liệu")).toHaveValue(
    "# Agent notes\n\nKeep this text after F5.",
  );
  await expect(page.getByText("Đã khôi phục bản nháp cục bộ")).toBeVisible();
  await expect(page.getByRole("button", { name: "Bỏ bản nháp cục bộ" })).toHaveCount(0);

  await page.goto("/graph");
  await page.goto("/documents");
  await expect(page.getByLabel("Tiêu đề tài liệu")).toHaveValue("Refresh-safe agent notes");
  await expect(page.getByLabel("Nội dung tài liệu")).toHaveValue(
    "# Agent notes\n\nKeep this text after F5.",
  );
  await expect(page.getByRole("button", { name: "Bỏ bản nháp cục bộ" })).toHaveCount(0);
});
