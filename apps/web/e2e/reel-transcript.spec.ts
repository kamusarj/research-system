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

test("researcher supplies a bounded Reel transcript without echoing its body", async ({ page }) => {
  let submitted: Record<string, unknown> | null = null;
  const item = {
    id: "reel-submission",
    url: "https://www.facebook.com/reel/123",
    source_type: "manual",
    status: "partial_success",
    stage: "completed",
    review_status: "needs_review",
    title: "Public Reel",
    content_preview: "Public metadata.",
    classification: {
      summary: "Public metadata.",
      normalized_source: {
        source_type: "facebook",
        collection_status: "PARTIAL",
        limitation_code: "TRANSCRIPT_UNAVAILABLE",
        limitation_message: "A transcript is unavailable.",
        metadata: { resource_kind: "reel" },
      },
    },
    transcript: {
      configured: false,
      language: null as string | null,
      segment_count: 0,
      updated_at: null as string | null,
    },
    provider_name: "mistral",
    model_name: null,
    attempt_count: 1,
    next_attempt_at: null,
    error: null,
    error_code: null,
    error_details: {},
    research_id: null,
    created_at: "2026-07-21T00:00:00Z",
    updated_at: "2026-07-21T00:01:00Z",
  };

  await page.route("**/api/v1/ai/providers", (route) => route.fulfill({
    json: [{ id: "mistral", configured: true, reachable: true, active: true, model: "test" }],
  }));
  await page.route("**/api/v1/ingestion/links**", async (route) => {
    if (route.request().method() === "PUT") {
      submitted = route.request().postDataJSON();
      item.status = "pending";
      item.stage = "pending";
      item.review_status = "not_requested";
      item.transcript = {
        configured: true,
        language: "vi",
        segment_count: 2,
        updated_at: "2026-07-21T00:02:00Z",
      };
      await route.fulfill({ json: item });
      return;
    }
    await route.fulfill({ json: [item] });
  });

  await page.goto("/ingestion");
  await page.getByRole("button", { name: "Thêm bản chép lời" }).click();
  await page.getByLabel("Bản chép lời có mốc thời gian").fill(
    "00:12 Mở đầu có bằng chứng\n01:02 Cần con người kiểm duyệt",
  );
  await page.getByRole("button", { name: "Lưu bản chép lời" }).click();

  await expect(page.getByText("Đã gắn bản chép lời do người dùng cung cấp · 2 đoạn")).toBeVisible();
  expect(submitted).toEqual({
    language: "vi",
    segments: [
      { timestamp_seconds: 12, text: "Mở đầu có bằng chứng" },
      { timestamp_seconds: 62, text: "Cần con người kiểm duyệt" },
    ],
  });
  await expect(page.getByText("Mở đầu có bằng chứng")).toHaveCount(0);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
});
