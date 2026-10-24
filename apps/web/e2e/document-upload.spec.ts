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

const uploaded = {
  id: "workspace",
  research_id: "research",
  attachment_id: "attachment",
  filename: "agent-memory.md",
  summary: "Human review and durable memory improve reliable agent decisions.",
  mime_type: "text/markdown",
  size_bytes: 25,
  content_hash: "a".repeat(64),
  processing_status: "uploaded",
  review_status: "not_requested",
  extraction_limitations: [],
  error_code: null,
  error_message: null,
  provider_name: "mistral",
  model_name: null,
  attempt_count: 0,
  next_attempt_at: null,
  started_at: null,
  finished_at: null,
  extracted_char_count: 0,
  graph_node_count: 0,
  graph_edge_count: 0,
  source_version: 1,
  editable: true,
  rag_status: "pending",
  rag_chunk_count: 0,
  rag_indexed_version: null,
  rag_error_code: null,
  rag_indexed_at: null,
  evaluation: null,
  created_at: "2026-07-18T00:00:00Z",
  updated_at: "2026-07-18T00:00:00Z",
};

test("uploaded PDF opens its editor from the uploaded-document list", async ({ page }) => {
  const source = "Agent memory\n\nHuman review remains required.";
  const pdfWorkspace = {
    ...uploaded,
    filename: "agent-memory.pdf",
    mime_type: "application/pdf",
    processing_status: "needs_review",
    review_status: "needs_review",
    extracted_char_count: source.length,
    rag_status: "ready",
    rag_chunk_count: 1,
    rag_indexed_version: 1,
  };

  await page.route("**/api/v1/documents**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === "/api/v1/documents") {
      return route.fulfill({ json: { items: [pdfWorkspace], total: 1 } });
    }
    if (path.endsWith("/content")) {
      return route.fulfill({
        json: {
          workspace_id: "workspace",
          filename: "agent-memory.pdf",
          format: "pdf",
          preview_kind: "pdf",
          source_text: source,
          extracted_text: source,
          supports_raw: true,
          source_truncated: false,
          editable: true,
          source_version: 1,
          editing_representation: "extracted_text",
          original_available: true,
          original_preview_kind: "pdf",
        },
      });
    }
    if (path.endsWith("/versions")) {
      return route.fulfill({ json: { items: [], total: 1 } });
    }
    if (path.endsWith("/graph")) {
      return route.fulfill({ json: { workspace_id: "workspace", nodes: [], edges: [], meta: {} } });
    }
    if (path.endsWith("/original")) {
      return route.fulfill({
        contentType: "application/pdf",
        body: Buffer.from("%PDF-1.4\n%%EOF"),
      });
    }
    return route.fulfill({ json: pdfWorkspace });
  });

  await page.goto("/documents");
  const filename = page.getByRole("link", { name: "agent-memory.pdf" });
  await expect(filename).toHaveAttribute("href", "/documents/workspace");
  await expect(page.getByRole("link", { name: "Xem phân tích" })).toHaveAttribute(
    "href",
    "/documents/workspace#document-analysis",
  );
  await filename.click();

  await expect(page).toHaveURL(/\/documents\/workspace$/);
  await expect(page.getByLabel("Nội dung tài liệu")).toHaveValue(source);
  await expect(page.getByText("Đang sửa văn bản đã trích xuất")).toBeVisible();
});

test("uploaded PDF keeps its original preview while editable text saves as a version", async ({ page }) => {
  let sourceVersion = 1;
  let source = "Agent memory\n\nHuman review remains required.";
  let savedPayload: { base_version: number; content: string } | null = null;
  const pdfWorkspace = () => ({
    ...uploaded,
    filename: "agent-memory.pdf",
    mime_type: "application/pdf",
    processing_status: "needs_review",
    review_status: "needs_review",
    extracted_char_count: source.length,
    source_version: sourceVersion,
    rag_status: "ready",
    rag_chunk_count: 1,
    rag_indexed_version: sourceVersion,
  });

  await page.route("**/api/v1/documents/workspace**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/original")) {
      return route.fulfill({
        status: 200,
        contentType: "application/pdf",
        body: Buffer.from("%PDF-1.4\n%%EOF"),
      });
    }
    if (path.endsWith("/content")) {
      return route.fulfill({
        json: {
          workspace_id: "workspace",
          filename: "agent-memory.pdf",
          format: "pdf",
          preview_kind: "pdf",
          source_text: source,
          extracted_text: source,
          supports_raw: true,
          source_truncated: false,
          editable: true,
          source_version: sourceVersion,
          editing_representation: "extracted_text",
          original_available: true,
          original_preview_kind: "pdf",
        },
      });
    }
    if (path.endsWith("/versions") && request.method() === "POST") {
      savedPayload = request.postDataJSON();
      source = savedPayload?.content ?? source;
      sourceVersion += 1;
      return route.fulfill({
        status: 201,
        json: {
          id: `version-${sourceVersion}`,
          version_number: sourceVersion,
          content_hash: "b".repeat(64),
          size_bytes: source.length,
          origin: "manual",
          change_summary: "Manual document edit",
          created_by: "local-user",
          created_at: "2026-08-09T08:00:00Z",
          current: true,
        },
      });
    }
    if (path.endsWith("/versions")) {
      return route.fulfill({ json: { items: [], total: sourceVersion } });
    }
    if (path.endsWith("/graph")) {
      return route.fulfill({
        json: { workspace_id: "workspace", nodes: [], edges: [], meta: {} },
      });
    }
    return route.fulfill({ json: pdfWorkspace() });
  });

  await page.goto("/documents/workspace");
  await expect(page.getByText("Đang sửa văn bản đã trích xuất")).toBeVisible();
  await expect(page.getByRole("link", { name: "Tải tệp gốc" }).first()).toHaveAttribute(
    "href",
    "/api/v1/documents/workspace/download",
  );
  await expect(page.getByTitle("Bản xem PDF gốc")).toHaveAttribute(
    "src",
    expect.stringContaining("/documents/workspace/original?inline=true"),
  );

  const editor = page.getByLabel("Nội dung tài liệu");
  await expect(editor).toHaveValue(source);
  await editor.fill(`${source}\n\nResearcher correction.`);
  await page.getByRole("button", { name: "Lưu phiên bản mới" }).click();
  await expect.poll(() => savedPayload).not.toBeNull();
  expect(savedPayload).toEqual({
    base_version: 1,
    content: "Agent memory\n\nHuman review remains required.\n\nResearcher correction.",
    change_summary: "Chỉnh sửa tài liệu thủ công",
  });

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
});

test("editable import and document brainstorm stay explicit and responsive", async ({ page }, testInfo) => {
  let uploadCount = 0;
  let brainstormCount = 0;
  let editCount = 0;
  await page.route("**/api/v1/documents", async (route) => {
    if (route.request().method() === "POST") {
      uploadCount += 1;
      await route.fulfill({ status: 201, json: uploaded });
      return;
    }
    await route.fulfill({ json: { items: [], total: 0 } });
  });
  await page.route("**/api/v1/documents/brainstorm", (route) => {
    brainstormCount += 1;
    return route.fulfill({
      json: {
        content: "Add a camera-angle ablation experiment.",
        provider_name: "deepseek",
        model_name: "deepseek-test",
        source_context_truncated: false,
      },
    });
  });
  await page.route("**/api/v1/documents/edit-in-place", async (route) => {
    editCount += 1;
    const request = route.request().postDataJSON();
    await route.fulfill({
      json: {
        source_revision: request.source_revision,
        selection_start: request.selection_start,
        selection_end: request.selection_end,
        original_text_hash: "a".repeat(64),
        replacement_text: request.source.replace("Agent memory", "Durable memory"),
        explanation: "Renamed the document heading.",
        risk: "medium",
        auto_apply_allowed: false,
        warnings: [],
        provider_name: "deepseek",
        model_name: "deepseek-test",
      },
    });
  });
  await page.route("**/api/v1/documents/workspace**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/content")) {
      return route.fulfill({
        json: {
          workspace_id: "workspace", filename: "agent-memory.md", format: "md",
          preview_kind: "markdown", source_text: "# Agent memory\nGoverned knowledge.",
          extracted_text: "Agent memory Governed knowledge.", supports_raw: true,
          source_truncated: false, editable: true, source_version: 1,
        },
      });
    }
    if (path.endsWith("/versions")) return route.fulfill({ json: { items: [], total: 0 } });
    return route.fulfill({ json: uploaded });
  });

  await page.goto("/documents");
  await page.getByLabel("Nhập nguồn có thể chỉnh sửa").setInputFiles({
    name: "agent-memory.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("# Agent memory\nGoverned knowledge."),
  });
  await expect(page.getByLabel("Tiêu đề tài liệu")).toHaveValue("agent-memory");
  const editor = page.getByLabel("Nội dung tài liệu");
  await expect(editor).toHaveValue("# Agent memory\nGoverned knowledge.");
  expect(uploadCount).toBe(0);

  const previewDisclosure = page.locator("details").filter({ hasText: "Xem trước tài liệu" });
  await expect(previewDisclosure).not.toHaveAttribute("open", "");
  await previewDisclosure.getByText("Xem trước tài liệu").click();
  await expect(previewDisclosure).toHaveAttribute("open", "");
  await expect(previewDisclosure.getByRole("button", { name: "Song song" })).toBeVisible();

  await page.getByRole("button", { name: "Sửa đoạn chọn hoặc đoạn hiện tại" }).click();
  await page.getByLabel("Tin nhắn").fill("What experiment is missing?");
  await page.getByRole("button", { name: "Gửi" }).click();
  await expect(page.getByText("Add a camera-angle ablation experiment.")).toBeVisible();
  await expect(editor).toHaveValue("# Agent memory\nGoverned knowledge.");
  await page.getByRole("button", { name: "Nối cuối tài liệu" }).click();
  await expect(editor).toHaveValue(
    "# Agent memory\nGoverned knowledge.\n\nAdd a camera-angle ablation experiment.",
  );
  expect(brainstormCount).toBe(1);

  const beforeChatEdit = await editor.inputValue();
  await page.evaluate(() => new Promise<void>((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
  }));
  const chatComposer = page.getByLabel("Tin nhắn");
  await chatComposer.fill("replace Agent memory with Durable memory");
  await expect(chatComposer).toHaveValue("replace Agent memory with Durable memory");
  await page.getByRole("button", { name: "Gửi" }).click();
  await expect(page.getByText("Duyệt thay đổi của AI")).toBeVisible();
  await expect(page.getByText("# Durable memory", { exact: false })).toBeVisible();
  await expect(editor).toHaveValue(beforeChatEdit);
  expect(brainstormCount).toBe(1);
  expect(editCount).toBe(1);
  await page.getByRole("button", { name: "Từ chối" }).click();
  await expect(editor).toHaveValue(beforeChatEdit);

  await chatComposer.fill("replace Agent memory with Durable memory");
  await expect(chatComposer).toHaveValue("replace Agent memory with Durable memory");
  await page.getByRole("button", { name: "Gửi" }).click();
  await expect(page.getByText("Duyệt thay đổi của AI")).toBeVisible();
  await page.getByRole("button", { name: "Chấp nhận thay đổi" }).click();
  await expect(editor).toHaveValue(beforeChatEdit.replace("Agent memory", "Durable memory"));
  expect(brainstormCount).toBe(1);
  expect(editCount).toBe(2);

  if (testInfo.project.name === "desktop-chrome") {
    await page.setViewportSize({ width: 1920, height: 1080 });
    const wideEditor = await page.getByLabel("Văn bản trong cửa sổ").boundingBox();
    const wideChat = await page.locator(".document-brainstorm").boundingBox();
    expect(wideEditor).not.toBeNull();
    expect(wideChat).not.toBeNull();
    expect(wideChat!.x).toBeGreaterThan(wideEditor!.x + wideEditor!.width);

    await page.setViewportSize({ width: 1366, height: 768 });
    const laptopMetrics = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      content: document.documentElement.scrollWidth,
    }));
    expect(laptopMetrics.content).toBeLessThanOrEqual(laptopMetrics.viewport);
  }

  await page.getByRole("button", { name: "Đóng cửa sổ chỉnh sửa" }).click();
  await page.getByRole("button", { name: "Tạo tài liệu" }).click();
  await expect.poll(() => uploadCount).toBe(1);
  await expect(page).toHaveURL(/\/documents\/workspace$/);

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
});

test("processed document exposes paper fit, graph and evidence", async ({ page }) => {
  const processed = {
    ...uploaded,
    processing_status: "needs_review",
    review_status: "needs_review",
    model_name: "mistral-large-latest",
    attempt_count: 1,
    extracted_char_count: 1600,
    graph_node_count: 1,
    evaluation: {
      id: "evaluation", rubric_version: "v1", fit_score: 77.75,
      decision: "draft_graph", failed_gates: [],
      dimension_scores: { system_fit: 85, business_applicability: 80 },
      matched_pillars: ["Agent System Architecture"], candidate_parents: [],
      contribution_types: [], overlaps_with: [], fills_gaps: [], limitations: [],
      reasoning_summary: "The paper contributes a grounded business-agent architecture.",
      confidence: 0.9, provider_name: "mistral", model_name: "mistral-large-latest",
      prompt_version: "v1", created_at: "2026-07-18T00:00:00Z",
    },
  };
  const graph = {
    workspace_id: "workspace",
    nodes: [{
      id: "claim", node_type: "claim", label: "Human approval improves reliability",
      summary: "Grounded finding", parent_node_id: null, confidence: 0.9,
      evidence_status: "supported",
      evidence: [{ id: "evidence", location: { section_heading: "Results" }, excerpt: "Human approval improves reliability.", extraction_method: "ai-extraction" }],
    }],
    edges: [], meta: { node_count: 1, edge_count: 0 },
  };
  await page.route("**/api/v1/documents/workspace**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/graph")) return route.fulfill({ json: graph });
    if (path.endsWith("/content")) {
      return route.fulfill({
        json: {
          workspace_id: "workspace", filename: "agent-memory.md", format: "md",
          preview_kind: "markdown", source_text: "# Agent memory",
          extracted_text: "Agent memory", supports_raw: true, source_truncated: false,
          editable: false, source_version: 1,
        },
      });
    }
    await route.fulfill({ json: processed });
  });

  await page.goto("/documents/workspace");
  await expect(page.getByText("77.75")).toBeVisible();
  await page.getByRole("button", { name: "Human approval improves reliability" }).press("Enter");
  await expect(page.getByText("Human approval improves reliability.")).toBeVisible();

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
});

test("LaTeX CV preview compiles and embeds a PDF", async ({ page }) => {
  let compiledSource = "";
  await page.route("**/api/v1/documents/latex/compile", async (route) => {
    compiledSource = route.request().postDataJSON().source;
    await route.fulfill({
      contentType: "application/pdf",
      headers: { "Cache-Control": "no-store" },
      body: Buffer.from("%PDF-1.7\n%%EOF"),
    });
  });
  await page.goto("/documents");
  await page.getByLabel("Nhập nguồn có thể chỉnh sửa").setInputFiles({
    name: "cv.tex",
    mimeType: "text/plain",
    buffer: Buffer.from([
      "\\documentclass{article}",
      "\\begin{document}",
      "\\sidesection{CHỨNG CHỈ}",
      "{\\fontsize{8.8}{11.2}\\selectfont",
      "Google Analytics 4 - 2025\\par",
      "Meta Digital Marketing - 2024\\par",
      "}",
      "\\vspace*{12mm}",
      "\\hspace*{10mm}\\begin{minipage}{127.5mm}",
      "\\RaggedRight",
      "{\\fontsize{24.5}{27}\\selectfont\\bfseries\\color{bodytext}ỨNG VIÊN MẪU}\\par",
      "\\end{minipage}",
      "\\mainsection{KINH NGHIỆM LÀM VIỆC}",
      "\\jobheading{DIGITAL MARKETING EXECUTIVE}{06/2024 - HIỆN TẠI}{Công ty ABC Retail}",
      "\\tightbullets",
      "\\item Lập kế hoạch nội dung đa kênh.",
      "\\closebullets",
      "\\end{document}",
    ].join("\n")),
  });

  const previewDisclosure = page.locator("details").filter({ hasText: "Xem trước tài liệu" });
  await previewDisclosure.getByText("Xem trước tài liệu").click();
  await previewDisclosure.getByRole("button", { name: "Xem trước" }).click();
  const frame = previewDisclosure.locator("iframe.latex-pdf-preview");
  await expect(frame).toBeVisible();
  await expect(frame).toHaveAttribute("src", /^blob:.*#toolbar=0&navpanes=0&view=Fit$/);
  expect(compiledSource).toContain("\\documentclass{article}");
  expect(compiledSource).toContain("\\jobheading");
});

test("whole-source LaTeX edit rejects provider explanation and preserves Raw", async ({ page }) => {
  const source = [
    "\\documentclass{article}",
    "\\begin{document}",
    "\\textbf{NGUYỄN MINH AN}",
    "\\end{document}",
  ].join("\n");
  await page.route("**/api/v1/documents/edit-in-place", async (route) => {
    const request = route.request().postDataJSON();
    await route.fulfill({
      json: {
        source_revision: request.source_revision,
        selection_start: request.selection_start,
        selection_end: request.selection_end,
        original_text_hash: "a".repeat(64),
        replacement_text: [
          "Tôi sẽ giúp bạn thay đổi tên trong CV.",
          "**Vị trí cần thay đổi:**",
          "```latex",
          "\\textbf{BÙI HOÀNG LINH}",
          "```",
        ].join("\n\n"),
        explanation: "Đổi tên theo yêu cầu.",
        risk: "medium",
        auto_apply_allowed: false,
        warnings: [],
        provider_name: "deepseek",
        model_name: "deepseek-test",
      },
    });
  });

  await page.goto("/documents");
  await page.getByLabel("Nhập nguồn có thể chỉnh sửa").setInputFiles({
    name: "cv.tex",
    mimeType: "application/x-tex",
    buffer: Buffer.from(source),
  });
  const editor = page.getByLabel("Nội dung tài liệu");
  await expect(editor).toHaveValue(source);
  await page.getByRole("button", { name: "Sửa đoạn chọn hoặc đoạn hiện tại" }).click();
  await page.getByLabel("Tin nhắn").fill("sửa tên thành Bùi Hoàng Linh");
  await page.getByRole("button", { name: "Gửi" }).click();

  await expect(page.getByText("AI trả về bản sửa chưa hoàn chỉnh.", { exact: false })).toBeVisible();
  await expect(page.getByText("Duyệt thay đổi của AI")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Chấp nhận thay đổi" })).toHaveCount(0);
  await expect(editor).toHaveValue(source);
});

test("LaTeX compile failure shows a safe actionable line reason", async ({ page }) => {
  const source = "\\documentclass{article}\\begin{document}[REDACTED_PHONE]\\end{document}";

  await page.goto("/documents");
  await page.getByLabel("Nhập nguồn có thể chỉnh sửa").setInputFiles({
    name: "broken-redaction.tex",
    mimeType: "application/x-tex",
    buffer: Buffer.from(source),
  });
  const previewDisclosure = page.locator("details").filter({ hasText: "Xem trước tài liệu" });
  await previewDisclosure.getByText("Xem trước tài liệu").click();
  await previewDisclosure.getByRole("button", { name: "Xem trước" }).click();

  await expect(previewDisclosure.getByText("Biên dịch LaTeX thất bại", { exact: false }))
    .toBeVisible();
  await expect(page.getByLabel("Nội dung tài liệu")).toHaveValue(source);
});

test("selected Markdown text is reviewed and accepted locally before Save", async ({ page }) => {
  const source = "# Agent memory\n\nOriginal selected text.";
  const sourceVersion = 1;
  const editable = {
    ...uploaded,
    processing_status: "needs_review",
    review_status: "needs_review",
    extracted_char_count: source.length,
    source_version: sourceVersion,
    rag_status: "ready",
    rag_chunk_count: 2,
    rag_indexed_version: sourceVersion,
  };
  const versions = () => ({
    items: [{
      id: `version-${sourceVersion}`,
      version_number: sourceVersion,
      content_hash: "a".repeat(64),
      size_bytes: source.length,
      origin: sourceVersion === 1 ? "upload" : "ai_edit",
      change_summary: sourceVersion === 1 ? "Initial uploaded source" : "AI improve edit",
      created_by: "local-user",
      created_at: "2026-08-02T10:00:00Z",
      current: true,
    }],
    total: sourceVersion,
  });
  const content = () => ({
    workspace_id: "workspace",
    filename: "agent-memory.md",
    format: "md",
    preview_kind: "markdown",
    source_text: source,
    extracted_text: source,
    supports_raw: true,
    source_truncated: false,
    editable: true,
    source_version: sourceVersion,
  });
  await page.route("**/api/v1/documents/brainstorm", (route) => route.fulfill({
    json: {
      content: "Add a latency comparison table.",
      provider_name: "deepseek",
      model_name: "deepseek-test",
      source_context_truncated: false,
    },
  }));
  await page.route("**/api/v1/documents/edit-in-place", async (route) => {
    const request = route.request().postDataJSON();
    await route.fulfill({
      json: {
        source_revision: request.source_revision,
        selection_start: request.selection_start,
        selection_end: request.selection_end,
        original_text_hash: "a".repeat(64),
        replacement_text: "Clearer selected text.",
        explanation: "Improved clarity while preserving meaning.",
        risk: "low",
        auto_apply_allowed: false,
        warnings: [],
        provider_name: "deepseek",
        model_name: "deepseek-test",
      },
    });
  });

  await page.route("**/api/v1/documents/workspace**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/content")) return route.fulfill({ json: content() });
    if (path.endsWith("/versions")) return route.fulfill({ json: versions() });
    if (path.endsWith("/graph")) {
      return route.fulfill({ json: { workspace_id: "workspace", nodes: [], edges: [], meta: {} } });
    }
    return route.fulfill({
      json: {
        ...editable,
        source_version: sourceVersion,
        extracted_char_count: source.length,
        rag_indexed_version: sourceVersion,
      },
    });
  });

  await page.goto("/documents/workspace");
  const editor = page.getByLabel("Nội dung tài liệu");
  await expect(editor).toHaveValue(source);
  await editor.focus();
  await editor.evaluate((node: HTMLTextAreaElement) => node.setSelectionRange(16, 38));
  await page.keyboard.press("Shift+ArrowRight");
  await page.getByRole("button", { name: "Viết tốt hơn" }).click();
  await expect(page.getByText("Duyệt thay đổi của AI")).toBeVisible();
  await expect(editor).toHaveValue(source);
  await expect(page.getByText("Clearer selected text.")).toBeVisible();
  await page.getByRole("button", { name: "Chấp nhận thay đổi" }).click();
  await expect(editor).toHaveValue("# Agent memory\n\nClearer selected text.");
  await expect(page.getByText(/AI đã sửa bản nháp cục bộ/)).toBeVisible();
  await expect(page.getByText(/Phiên bản nguồn\s*1/)).toBeVisible();

  await page.getByRole("button", { name: "Hoàn tác" }).click();
  await expect(editor).toHaveValue(source);

  const focusEditor = page.getByLabel("Văn bản trong cửa sổ");
  await expect(focusEditor).toHaveValue(source);
  await focusEditor.focus();
  await focusEditor.evaluate((node: HTMLTextAreaElement) => node.setSelectionRange(16, 38));
  await page.keyboard.press("Shift+ArrowRight");
  await page.getByRole("button", { name: "Viết tốt hơn" }).click();
  await page.getByRole("button", { name: "Chấp nhận thay đổi" }).click();
  await expect(editor).toHaveValue("# Agent memory\n\nClearer selected text.");
  await expect(page.getByRole("button", { name: "Lưu phiên bản mới" })).toBeEnabled();

  await page.getByLabel("Tin nhắn").fill("What evidence should be added?");
  await page.getByRole("button", { name: "Gửi" }).click();
  await expect(page.getByText("Add a latency comparison table.")).toBeVisible();
  await expect(editor).toHaveValue("# Agent memory\n\nClearer selected text.");
  await page.getByRole("button", { name: "Nối cuối tài liệu" }).click();
  await expect(editor).toHaveValue(
    "# Agent memory\n\nClearer selected text.\n\nAdd a latency comparison table.",
  );

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
});
