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
        name: "Local owner",
        email: "local@research.system",
        role: "owner",
        active: true,
        password_configured: false,
      },
    },
  }));
});

test("graph chat creates a locally governed knowledge proposal", async ({ page }, testInfo) => {
  const session = {
    id: "session-1",
    title: "Agent governance",
    scope_type: "graph",
    scope_id: null,
    provider_name: "openai",
    model_name: "gpt-test",
    conversation_summary: "",
    status: "active",
    prompt_version: "graph-chat-v1",
    source_type: "local" as const,
    source_url: null,
    source_snapshot_hash: null,
    source_imported_at: null,
    imported_message_count: 0,
    message_count: 0,
    created_at: "2026-07-18T00:00:00Z",
    updated_at: "2026-07-18T00:00:00Z",
  };
  type Message = {
    id: string;
    session_id: string;
    role: "user" | "assistant";
    content: string;
    provider_response_id: string | null;
    provider_request_id: string | null;
    tool_calls: Array<{ call_id: string; name: string; arguments: object }>;
    tool_results: object[];
    linked_change_set_id: string | null;
    usage: object;
    latency_ms: number | null;
    error_code: string | null;
    origin_type: "local" | "chatgpt_shared";
    media: Array<{ type: "image"; url: string; alt: string }>;
    created_at: string;
  };
  const messages: Message[] = [];
  let sessions: typeof session[] = [];

  await page.route("**/api/v1/ai/providers", (route) => route.fulfill({
    json: [{ id: "openai", configured: true, reachable: null, active: false, model: "gpt-test" }],
  }));
  await page.route("**/api/v1/chat/sessions", async (route) => {
    if (route.request().method() === "POST") {
      sessions = [session];
      await route.fulfill({ status: 201, json: session });
      return;
    }
    await route.fulfill({ json: { items: sessions, total: sessions.length } });
  });
  await page.route("**/api/v1/chat/sessions/session-1/messages", async (route) => {
    if (route.request().method() === "POST") {
      const user: Message = {
        id: "user-1", session_id: session.id, role: "user",
        content: "Propose an adaptive evaluator agent.",
        provider_response_id: null, provider_request_id: null,
        tool_calls: [], tool_results: [], linked_change_set_id: null,
        usage: {}, latency_ms: null, error_code: null,
        origin_type: "local",
        media: [],
        created_at: "2026-07-18T00:01:00Z",
      };
      const assistant: Message = {
        ...user, id: "assistant-1", role: "assistant",
        content: "I created a draft evaluator proposal for human review.",
        provider_response_id: "response-1", provider_request_id: "request-1",
        tool_calls: [{ call_id: "call-1", name: "propose_node", arguments: {} }],
        linked_change_set_id: "change-set-1", usage: { total_tokens: 42 }, latency_ms: 120,
      };
      messages.push(user, assistant);
      session.message_count = messages.length;
      await route.fulfill({ json: {
        session, user_message: user, assistant_message: assistant,
        change_set_id: "change-set-1",
      } });
      return;
    }
    await route.fulfill({ json: messages });
  });

  await page.goto("/chat");
  await page.getByRole("button", { name: "Cuộc trò chuyện mới" }).click();
  await page.getByLabel("Tiêu đề").fill("Agent governance");
  await page.getByRole("button", { name: "Tạo cuộc trò chuyện" }).click();
  await expect(page.getByRole("heading", { name: "Hôm nay, bạn muốn khám phá điều gì?" })).toBeInViewport({ ratio: 1 });
  await page.screenshot({ path: `/tmp/ai-chat-start-${testInfo.project.name}.png`, animations: "disabled" });
  await page.getByRole("button", { name: /Phát triển ý tưởng/ }).click();
  await expect(page.getByLabel("Tin nhắn")).toHaveValue(/Tôi muốn phát triển một ý tưởng/);
  expect(messages).toHaveLength(0);
  await page.getByLabel("Tin nhắn").press("Shift+Enter");
  await expect(page.getByLabel("Tin nhắn")).toHaveValue(/\n$/);
  await page.getByLabel("Tin nhắn").dispatchEvent("keydown", { key: "Enter", code: "Enter", isComposing: true });
  expect(messages).toHaveLength(0);
  await page.getByLabel("Tin nhắn").fill("Propose an adaptive evaluator agent.");
  await page.getByLabel("Tin nhắn").press("Enter");

  await expect(page.getByText("I created a draft evaluator proposal for human review.")).toBeVisible();
  await expect(page.getByRole("link", { name: /Duyệt thay đổi tri thức/ })).toHaveAttribute(
    "href",
    "/graph/changes/change-set-1",
  );
  const selectedPassage = page.getByText("I created a draft evaluator proposal for human review.");
  await selectedPassage.selectText();
  await selectedPassage.dispatchEvent("mouseup");
  await expect(page.getByRole("toolbar", { name: "Thao tác với đoạn đã chọn" })).toBeVisible();
  await page.getByRole("button", { name: "Hỏi AI" }).click();
  await expect(page.getByLabel("Tin nhắn")).toHaveValue(
    /Hãy giúp tôi phân tích đoạn đã chọn này:[\s\S]*draft evaluator proposal/,
  );
  expect(messages).toHaveLength(2);
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
  const sendBox = await page.getByRole("button", { name: "Gửi", exact: true }).boundingBox();
  expect(sendBox).not.toBeNull();
  expect(sendBox!.y + sendBox!.height).toBeLessThanOrEqual(page.viewportSize()!.height);
  await page.screenshot({ path: `/tmp/ai-chat-conversation-${testInfo.project.name}.png`, animations: "disabled" });
  if (testInfo.project.name === "desktop-chrome") {
    for (const viewport of [
      { width: 1366, height: 768 },
      { width: 1920, height: 1080 },
    ]) {
      await page.setViewportSize(viewport);
      await expect(page.getByLabel("Tin nhắn")).toBeInViewport();
      const windowsFit = await page.evaluate(() => ({
        viewport: document.documentElement.clientWidth,
        content: document.documentElement.scrollWidth,
      }));
      expect(windowsFit.content).toBeLessThanOrEqual(windowsFit.viewport);
    }
  }
});

test("chat history search and historical errors stay readable", async ({ page }, testInfo) => {
  const session = {
    id: "historical-session", title: "Phân tích kiến trúc tác nhân AI", scope_type: "graph",
    scope_id: null, provider_name: "openai", model_name: "gpt-test", status: "active",
    source_type: "local", message_count: 2, updated_at: "2026-09-05T07:00:00Z",
  };
  await page.route("**/api/v1/ai/providers", (route) => route.fulfill({ json: [
    { id: "openai", configured: false, model: "gpt-test" },
    { id: "deepseek", configured: true, chat_active: true, model: "deepseek-test" },
  ] }));
  await page.route("**/api/v1/chat/sessions", (route) => route.fulfill({ json: { items: [session], total: 1 } }));
  await page.route("**/api/v1/chat/sessions/historical-session/messages", (route) => route.fulfill({ json: [
    { id: "u1", role: "user", content: "Hãy giúp tôi phân tích kiến trúc hệ thống tác nhân AI cho doanh nghiệp.", media: [], created_at: "2026-09-05T07:00:00Z" },
    { id: "a1", role: "assistant", content: "OpenAI chat credentials are unavailable", error_code: "CHAT_PROVIDER_UNAVAILABLE", media: [], created_at: "2026-09-05T07:00:02Z" },
  ] }));
  await page.goto("/chat");
  await expect(page.getByText("Chưa thể hoàn tất câu trả lời")).toBeVisible();
  await expect(page.getByText("OpenAI chat credentials are unavailable")).toHaveCount(0);
  await expect(page.getByText("CHAT_PROVIDER_UNAVAILABLE", { exact: true })).not.toBeVisible();
  await page.getByText("Chi tiết lỗi", { exact: true }).click();
  await expect(page.getByText("CHAT_PROVIDER_UNAVAILABLE", { exact: true })).toBeVisible();
  if (testInfo.project.name === "mobile-chrome") await page.getByRole("button", { name: "Lịch sử trò chuyện" }).click();
  await page.getByLabel("Tìm cuộc trò chuyện").fill("phan tich kien truc");
  await expect(page.locator(".chat-session-list > button")).toHaveCount(1);
  await page.getByLabel("Tìm cuộc trò chuyện").fill("không tồn tại");
  await expect(page.getByText("Không tìm thấy cuộc trò chuyện phù hợp.")).toBeVisible();
  await page.getByLabel("Tìm cuộc trò chuyện").fill("");
  await page.locator(".chat-session-list > button").click();
  await expect(page.getByLabel("Tin nhắn", { exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Chọn AI cho cuộc trò chuyện mới" }).click();
  await expect(page.getByText("Bắt đầu một mạch suy nghĩ mới")).toBeVisible();
  await page.getByRole("button", { name: "Quay lại trò chuyện" }).click();
  await page.screenshot({ path: `/tmp/ai-chat-error-${testInfo.project.name}.png`, animations: "disabled" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
});

test("imports a public ChatGPT snapshot and keeps continuation local", async ({ page }) => {
  const sourceUrl = "https://chatgpt.com/share/12345678-1234-1234-1234-123456789abc";
  const importedSession = {
    id: "imported-session",
    title: "Imported agent plan",
    scope_type: "graph",
    scope_id: null,
    provider_name: "deepseek",
    model_name: "deepseek-test",
    conversation_summary: "",
    status: "active",
    prompt_version: "graph-chat-v1",
    source_type: "chatgpt_shared",
    source_url: sourceUrl,
    source_snapshot_hash: "a".repeat(64),
    source_imported_at: "2026-08-01T00:00:00Z",
    imported_message_count: 2,
    message_count: 2,
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
  };
  const importedMessages = [
    {
      id: "imported-user",
      session_id: importedSession.id,
      role: "user",
      content: "Plan a governed agent.",
      provider_response_id: null,
      provider_request_id: null,
      tool_calls: [],
      tool_results: [],
      linked_change_set_id: null,
      usage: {},
      latency_ms: null,
      error_code: null,
      origin_type: "chatgpt_shared",
      media: [{
        type: "image",
        url: "/api/v1/chat/messages/imported-user/media/0",
        alt: "Governed agent diagram",
      }],
      created_at: "2026-08-01T00:00:00Z",
    },
    {
      id: "imported-assistant",
      session_id: importedSession.id,
      role: "assistant",
      content: "Use a human review gate.",
      provider_response_id: null,
      provider_request_id: null,
      tool_calls: [],
      tool_results: [],
      linked_change_set_id: null,
      usage: {},
      latency_ms: null,
      error_code: null,
      origin_type: "chatgpt_shared",
      media: [],
      created_at: "2026-08-01T00:00:00.000001Z",
    },
  ];
  let sessions: typeof importedSession[] = [];

  await page.route("**/api/v1/ai/providers", (route) => route.fulfill({
    json: [{ id: "deepseek", configured: true, reachable: null, chat_active: true, model: "deepseek-test" }],
  }));
  await page.route("**/api/v1/chat/messages/imported-user/media/0", (route) => route.fulfill({
    contentType: "image/png",
    body: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
      "base64",
    ),
  }));
  await page.route("**/api/v1/chat/imports/chatgpt", async (route) => {
    expect(route.request().postDataJSON()).toEqual({ url: sourceUrl, provider: "deepseek" });
    sessions = [importedSession];
    await route.fulfill({ status: 201, json: importedSession });
  });
  await page.route("**/api/v1/chat/sessions", (route) => route.fulfill({
    json: { items: sessions, total: sessions.length },
  }));
  await page.route("**/api/v1/chat/sessions/imported-session/messages", async (route) => {
    if (route.request().method() === "POST") {
      const localUser = {
        ...importedMessages[0],
        id: "local-user",
        content: "Continue locally.",
        origin_type: "local",
      };
      const localAssistant = {
        ...importedMessages[1],
        id: "local-assistant",
        content: "This continuation is stored locally.",
        origin_type: "local",
      };
      importedMessages.push(localUser, localAssistant);
      importedSession.message_count = importedMessages.length;
      await route.fulfill({ json: {
        session: importedSession,
        user_message: localUser,
        assistant_message: localAssistant,
        change_set_id: null,
      } });
      return;
    }
    await route.fulfill({ json: importedMessages });
  });

  await page.goto("/chat");
  await page.getByRole("button", { name: "Nhập từ ChatGPT" }).click();
  await page.getByLabel("Liên kết chia sẻ ChatGPT").fill(sourceUrl);
  await page.getByRole("button", { name: "Nhập cuộc trò chuyện", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Imported agent plan" })).toBeVisible();
  await expect(page.getByText("Bản chụp đã nhập")).toHaveCount(2);
  await expect(page.getByRole("img", { name: "Governed agent diagram" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Bản chụp ChatGPT công khai" })).toHaveAttribute(
    "href",
    sourceUrl,
  );
  await page.getByLabel("Tin nhắn").fill("Continue locally.");
  await page.getByRole("button", { name: "Gửi" }).click();
  await expect(page.getByText("This continuation is stored locally.")).toBeVisible();
  await expect(page.getByText("Bản chụp đã nhập")).toHaveCount(2);
});
