import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { DocumentAIEditor } from "./document-ai-editor";
import type { DocumentContent, DocumentWorkspace } from "@/lib/types";

const mocks = vi.hoisted(() => ({
  instantEdit: vi.fn(),
  saveSource: vi.fn(),
  restoreSource: vi.fn(),
  rebuildRag: vi.fn(),
  brainstormDocument: vi.fn(),
  api: vi.fn(),
}));

vi.mock("@/lib/i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: mocks.api };
});
vi.mock("@/lib/documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/documents")>("@/lib/documents");
  return {
    ...actual,
    requestDocumentInstantEdit: mocks.instantEdit,
    saveDocumentSource: mocks.saveSource,
    restoreDocumentSource: mocks.restoreSource,
    rebuildDocumentRag: mocks.rebuildRag,
    brainstormDocument: mocks.brainstormDocument,
  };
});

const workspace: DocumentWorkspace = {
  id: "workspace-1",
  research_id: "research-1",
  attachment_id: "attachment-1",
  filename: "agents.md",
  summary: "A concise document about business agents.",
  mime_type: "text/markdown",
  size_bytes: 50,
  content_hash: "a".repeat(64),
  processing_status: "needs_review",
  review_status: "needs_review",
  extraction_limitations: [],
  error_code: null,
  error_message: null,
  provider_name: "mistral",
  model_name: "mistral-large-latest",
  attempt_count: 1,
  next_attempt_at: null,
  started_at: null,
  finished_at: null,
  extracted_char_count: 36,
  graph_node_count: 0,
  graph_edge_count: 0,
  source_version: 1,
  editable: true,
  rag_status: "ready",
  rag_chunk_count: 2,
  rag_indexed_version: 1,
  rag_error_code: null,
  rag_indexed_at: "2026-08-02T10:00:00Z",
  evaluation: null,
  created_at: "2026-08-02T09:00:00Z",
  updated_at: "2026-08-02T10:00:00Z",
};

const content: DocumentContent = {
  workspace_id: "workspace-1",
  filename: "agents.md",
  format: "md",
  preview_kind: "markdown",
  source_text: "# Agents\n\nOriginal selected text.",
  extracted_text: "Agents\n\nOriginal selected text.",
  supports_raw: true,
  source_truncated: false,
  editable: true,
  source_version: 1,
};

function renderEditor(
  onChanged = vi.fn().mockResolvedValue(undefined),
  contentValue: DocumentContent = content,
  workspaceValue: DocumentWorkspace = workspace,
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    onChanged,
    ...render(
      <QueryClientProvider client={queryClient}>
        <DocumentAIEditor
          workspace={workspaceValue}
          content={contentValue}
          userId="owner-one"
          canEdit
          onChanged={onChanged}
        />
      </QueryClientProvider>,
    ),
  };
}

it("labels an editable PDF derivative and keeps the original preview available", async () => {
  renderEditor(
    vi.fn().mockResolvedValue(undefined),
    {
      ...content,
      filename: "agents.pdf",
      format: "pdf",
      preview_kind: "pdf",
      editing_representation: "extracted_text",
      original_available: true,
      original_preview_kind: "pdf",
    },
    { ...workspace, filename: "agents.pdf", mime_type: "application/pdf" },
  );

  expect(await screen.findByText("editingExtractedText")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "downloadOriginal" })).toHaveAttribute(
    "href",
    "/api/v1/documents/workspace-1/original",
  );
  expect(screen.getByTitle("originalPdfPreview")).toHaveAttribute(
    "src",
    expect.stringContaining("/documents/workspace-1/original?inline=true"),
  );
  expect(screen.getByLabelText("documentBody")).toHaveValue(content.source_text);
});

beforeEach(() => {
  window.localStorage.clear();
  Object.values(mocks).forEach((mock) => mock.mockReset());
  mocks.api.mockResolvedValue({
    items: [{
      id: "version-1",
      version_number: 1,
      content_hash: "a".repeat(64),
      size_bytes: 50,
      origin: "upload",
      change_summary: "Initial uploaded source",
      created_by: "owner-one",
      created_at: "2026-08-02T09:00:00Z",
      current: true,
    }],
    total: 1,
  });
  mocks.brainstormDocument.mockResolvedValue({
    content: "Replacement drafted in chat.",
    provider_name: "deepseek",
    model_name: "deepseek-test",
    source_context_truncated: false,
  });
  mocks.instantEdit.mockImplementation(async (input) => ({
    source_revision: input.sourceRevision,
    selection_start: input.selectionStart,
    selection_end: input.selectionEnd,
    original_text_hash: "a".repeat(64),
    replacement_text: "Clearer selected text.",
    explanation: "Improved clarity.",
    risk: "low",
    auto_apply_allowed: true,
    warnings: [],
    provider_name: "deepseek",
    model_name: "deepseek-test",
  }));
});

function openChatWindow(editor: HTMLTextAreaElement) {
  if (editor.selectionStart === editor.selectionEnd) {
    editor.setSelectionRange(0, editor.value.length);
    fireEvent.select(editor);
  }
  fireEvent.click(screen.getByRole("button", { name: /askAiToEdit/ }));
}

it("shows selection options again after closing the window with a pending review", async () => {
  renderEditor();
  const editor = await screen.findByLabelText("documentBody") as HTMLTextAreaElement;
  editor.setSelectionRange(10, 33);
  fireEvent.select(editor);

  fireEvent.click(screen.getByRole("button", { name: "aiEditAction.improve" }));
  expect(await screen.findByText("instantEditReviewRequired")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "closeFocusWindow" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

  editor.setSelectionRange(10, 33);
  fireEvent.select(editor);
  expect(await screen.findByRole("button", { name: "aiEditAction.improve" })).toBeInTheDocument();
});

it("restores an unsaved workspace edit after remount", async () => {
  const first = renderEditor();
  const editor = await screen.findByLabelText("documentBody");
  fireEvent.change(editor, { target: { value: "# Agents\n\nUnsaved browser edit." } });
  expect(screen.getByText("draftSavedLocally")).toBeInTheDocument();
  first.unmount();

  renderEditor();
  await waitFor(() => expect(
    (screen.getByLabelText("documentBody") as HTMLTextAreaElement).value,
  ).toBe("# Agents\n\nUnsaved browser edit."));
  expect(screen.getByText("editorDraftRestored")).toBeInTheDocument();
});

it("shows a diff and requires accept before changing selected text locally", async () => {
  renderEditor();
  const editor = await screen.findByLabelText("documentBody") as HTMLTextAreaElement;
  editor.setSelectionRange(10, 33);
  fireEvent.select(editor);

  fireEvent.click(screen.getByRole("button", { name: "aiEditAction.improve" }));
  const review = (await screen.findByText("instantEditReviewRequired")).closest("article");
  expect(editor.value).toContain("Original selected text.");
  expect(review).toHaveTextContent("Original selected text.");
  expect(review).toHaveTextContent("Clearer selected text.");
  fireEvent.click(screen.getByRole("button", { name: "acceptAiEdit" }));
  await waitFor(() => expect(editor.value).toContain("Clearer selected text."));
  expect(editor.value).not.toContain("Original selected text.");
  expect(screen.getByText(/instantEditApplied/)).toBeInTheDocument();
  expect(mocks.saveSource).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "undoInstantEdit" }));
  expect(editor.value).toContain("Original selected text.");
  expect(editor.value).not.toContain("Clearer selected text.");
});

it("rejects a protected reviewed edit without changing the draft", async () => {
  mocks.instantEdit.mockImplementation(async (input) => ({
    source_revision: input.sourceRevision,
    selection_start: input.selectionStart,
    selection_end: input.selectionEnd,
    original_text_hash: "b".repeat(64),
    replacement_text: "Protected replacement.",
    explanation: "A number may change.",
    risk: "high",
    auto_apply_allowed: false,
    warnings: ["protected_numbers"],
    provider_name: "deepseek",
    model_name: "deepseek-test",
  }));
  renderEditor();
  const editor = await screen.findByLabelText("documentBody") as HTMLTextAreaElement;
  editor.setSelectionRange(10, 33);
  fireEvent.select(editor);

  fireEvent.click(screen.getByRole("button", { name: "aiEditAction.shorten" }));
  expect(await screen.findByText("instantEditReviewRequired")).toBeInTheDocument();
  expect(editor.value).toContain("Original selected text.");
  fireEvent.click(screen.getByRole("button", { name: "rejectAiEdit" }));
  expect(editor.value).toContain("Original selected text.");
  expect(editor.value).not.toContain("Protected replacement.");
  expect(mocks.saveSource).not.toHaveBeenCalled();
});

it("brainstorms beside uploaded source and replaces text only after explicit apply", async () => {
  renderEditor();
  const editor = await screen.findByLabelText("documentBody") as HTMLTextAreaElement;
  editor.setSelectionRange(10, 33);
  fireEvent.select(editor);
  openChatWindow(editor);
  fireEvent.change(screen.getByLabelText("chatMessage"), {
    target: { value: "Draft a clearer alternative" },
  });
  fireEvent.click(screen.getByRole("button", { name: "sendMessage" }));

  expect(await screen.findByText("Replacement drafted in chat.")).toBeInTheDocument();
  expect(editor.value).toContain("Original selected text.");
  fireEvent.click(screen.getByRole("button", { name: "replaceSelection" }));
  expect(editor.value).toContain("Replacement drafted in chat.");
  expect(editor.value).not.toContain("Original selected text.");
  expect(screen.getByText("draftSavedLocally")).toBeInTheDocument();
});

it("routes an uploaded-document chat edit command to Accept or Reject", async () => {
  renderEditor();
  const editor = await screen.findByLabelText("documentBody") as HTMLTextAreaElement;
  editor.setSelectionRange(10, 33);
  fireEvent.select(editor);
  openChatWindow(editor);
  fireEvent.change(screen.getByLabelText("chatMessage"), {
    target: { value: "replace this with clearer wording" },
  });
  fireEvent.click(screen.getByRole("button", { name: "sendMessage" }));

  const review = (await screen.findByText("instantEditReviewRequired")).closest("article");
  expect(review).toHaveTextContent("Original selected text.");
  expect(review).toHaveTextContent("Clearer selected text.");
  expect(await screen.findByText("documentChatEditReady")).toBeInTheDocument();
  expect(editor.value).toContain("Original selected text.");
  expect(mocks.brainstormDocument).not.toHaveBeenCalled();
  expect(mocks.instantEdit).toHaveBeenCalledWith(expect.objectContaining({
    selectionStart: 10,
    selectionEnd: 33,
    action: "custom",
    instruction: "replace this with clearer wording",
  }));

  fireEvent.click(screen.getByRole("button", { name: "rejectAiEdit" }));
  expect(editor.value).toContain("Original selected text.");
  expect(editor.value).not.toContain("Clearer selected text.");
});
