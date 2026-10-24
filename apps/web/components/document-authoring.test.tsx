import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { DocumentAuthoring } from "./document-authoring";
import { ApiError } from "@/lib/api";
import {
  documentDraftStorageKey,
  emptyDocumentAuthorDraft,
  readDocumentAuthorDraft,
  writeDocumentAuthorDraft,
} from "@/lib/documents";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  uploadDocument: vi.fn(),
  brainstormDocument: vi.fn(),
  instantEdit: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push }),
}));

vi.mock("@/lib/i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

vi.mock("@/lib/documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/documents")>("@/lib/documents");
  return {
    ...actual,
    uploadDocument: mocks.uploadDocument,
    brainstormDocument: mocks.brainstormDocument,
    requestDocumentInstantEdit: mocks.instantEdit,
  };
});

beforeEach(() => {
  window.localStorage.clear();
  mocks.push.mockReset();
  mocks.uploadDocument.mockReset();
  mocks.uploadDocument.mockResolvedValue({ id: "workspace-created" });
  mocks.brainstormDocument.mockReset();
  mocks.brainstormDocument.mockResolvedValue({
    content: "Thêm thí nghiệm thay đổi góc camera.",
    provider_name: "deepseek",
    model_name: "deepseek-test",
    source_context_truncated: false,
  });
  mocks.instantEdit.mockImplementation(async (input) => ({
    source_revision: input.sourceRevision,
    selection_start: input.selectionStart,
    selection_end: input.selectionEnd,
    original_text_hash: "a".repeat(64),
    replacement_text: "Clear camera baseline.",
    explanation: "Improved clarity.",
    risk: "low",
    auto_apply_allowed: true,
    warnings: [],
    provider_name: "deepseek",
    model_name: "deepseek-test",
  }));
});

function openChatWindow(editor: HTMLTextAreaElement) {
  editor.setSelectionRange(0, editor.value.length);
  fireEvent.select(editor);
  fireEvent.click(screen.getByRole("button", { name: /askAiToEdit/ }));
}

it("autosaves every edit, restores after remount, and exposes no manual discard", async () => {
  const key = documentDraftStorageKey("owner-one");
  writeDocumentAuthorDraft(window.localStorage, key, {
    ...emptyDocumentAuthorDraft(),
    title: "Agent memory",
    content: "# Durable memory",
    updatedAt: "2026-07-30T15:00:00.000Z",
  });

  const { unmount } = render(<DocumentAuthoring userId="owner-one" />);

  expect(await screen.findByDisplayValue("Agent memory")).toBeInTheDocument();
  expect(screen.getByText("draftRestored")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("documentBody"), {
    target: { value: "# Durable memory\n\nHuman review." },
  });

  expect(readDocumentAuthorDraft(window.localStorage, key)?.content).toContain("Human review.");
  expect(screen.getByText("draftSavedLocally")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "discardLocalDraft" })).not.toBeInTheDocument();

  unmount();
  render(<DocumentAuthoring userId="owner-one" />);

  expect(await screen.findByDisplayValue("Agent memory")).toBeInTheDocument();
  expect(screen.getByLabelText("documentBody")).toHaveValue(
    "# Durable memory\n\nHuman review.",
  );
  expect(screen.getByText("draftRestored")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "discardLocalDraft" })).not.toBeInTheDocument();
});

it("creates through the governed upload helper and clears cache only after success", async () => {
  const key = documentDraftStorageKey("owner-one");
  render(<DocumentAuthoring userId="owner-one" />);

  fireEvent.change(screen.getByLabelText("documentTitle"), {
    target: { value: "Governed workflow" },
  });
  fireEvent.change(screen.getByLabelText("documentBody"), {
    target: { value: "# Workflow\n\nCite source evidence." },
  });
  expect(readDocumentAuthorDraft(window.localStorage, key)).not.toBeNull();

  fireEvent.click(screen.getByRole("button", { name: "createAuthoredDocument" }));

  await waitFor(() => expect(mocks.uploadDocument).toHaveBeenCalledOnce());
  const file = mocks.uploadDocument.mock.calls[0][0] as File;
  expect(file.name).toBe("Governed workflow.md");
  expect(file.type).toBe("text/markdown");
  await waitFor(() => expect(window.localStorage.getItem(key)).toBeNull());
  expect(mocks.push).toHaveBeenCalledWith("/documents/workspace-created");
});

it("retains the cached draft when creation fails", async () => {
  mocks.uploadDocument.mockRejectedValue(new Error("Server unavailable"));
  const key = documentDraftStorageKey("owner-one");
  render(<DocumentAuthoring userId="owner-one" />);

  fireEvent.change(screen.getByLabelText("documentTitle"), {
    target: { value: "Keep this draft" },
  });
  fireEvent.change(screen.getByLabelText("documentBody"), {
    target: { value: "Unsaved but cached content." },
  });
  fireEvent.click(screen.getByRole("button", { name: "createAuthoredDocument" }));

  expect(await screen.findByText("Server unavailable")).toBeInTheDocument();
  expect(readDocumentAuthorDraft(window.localStorage, key)?.content).toBe(
    "Unsaved but cached content.",
  );
  expect(mocks.push).not.toHaveBeenCalled();
});

it("imports editable source into Document content before upload", async () => {
  render(<DocumentAuthoring userId="owner-one" />);
  const file = new File(
    ["\\section{Robot}\nCamera and control experiments."],
    "robot-study.tex",
    { type: "application/x-tex" },
  );

  fireEvent.change(screen.getByLabelText("importEditableSource"), {
    target: { files: [file] },
  });

  expect(await screen.findByDisplayValue("robot-study")).toBeInTheDocument();
  expect(screen.getByLabelText("documentBody")).toHaveValue(
    "\\section{Robot}\nCamera and control experiments.",
  );
  expect(mocks.uploadDocument).not.toHaveBeenCalled();
});

it("brainstorms on current content and appends only after explicit apply", async () => {
  render(<DocumentAuthoring userId="owner-one" />);
  fireEvent.change(screen.getByLabelText("documentTitle"), {
    target: { value: "Robot experiments" },
  });
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: "Camera baseline." } });
  openChatWindow(editor);
  fireEvent.change(screen.getByLabelText("chatMessage"), {
    target: { value: "Cần thêm thí nghiệm gì?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "sendMessage" }));

  expect(await screen.findByText("Thêm thí nghiệm thay đổi góc camera.")).toBeInTheDocument();
  expect(screen.getByLabelText("documentBody")).toHaveValue("Camera baseline.");
  fireEvent.click(screen.getByRole("button", { name: "appendToDocument" }));
  expect(screen.getByLabelText("documentBody")).toHaveValue(
    "Camera baseline.\n\nThêm thí nghiệm thay đổi góc camera.",
  );
  expect(mocks.uploadDocument).not.toHaveBeenCalled();
});

it("routes a chat rename command to the reviewed instant-edit diff", async () => {
  const source = "\\textbf{NGUYỄN MINH AN}";
  const replacement = "\\textbf{BÙI HOÀNG LINH}";
  mocks.instantEdit.mockImplementationOnce(async (input) => ({
    source_revision: input.sourceRevision,
    selection_start: input.selectionStart,
    selection_end: input.selectionEnd,
    original_text_hash: "a".repeat(64),
    replacement_text: replacement,
    explanation: "Đổi tên theo yêu cầu.",
    risk: "medium",
    auto_apply_allowed: false,
    warnings: [],
    provider_name: "deepseek",
    model_name: "deepseek-test",
  }));
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: source } });
  openChatWindow(editor);
  fireEvent.change(screen.getByLabelText("chatMessage"), {
    target: { value: "sửa tên thành Bùi Hoàng Linh" },
  });
  fireEvent.click(screen.getByRole("button", { name: "sendMessage" }));

  const review = (await screen.findByText("instantEditReviewRequired")).closest("article");
  expect(review).toHaveTextContent(source);
  expect(review).toHaveTextContent(replacement);
  expect(await screen.findByText("documentChatEditReady")).toBeInTheDocument();
  expect(editor.value).toBe(source);
  expect(mocks.brainstormDocument).not.toHaveBeenCalled();
  expect(mocks.instantEdit).toHaveBeenCalledWith(expect.objectContaining({
    source,
    selectionStart: 0,
    selectionEnd: source.length,
    action: "custom",
    instruction: "sửa tên thành Bùi Hoàng Linh",
  }));

  fireEvent.click(screen.getByRole("button", { name: "acceptAiEdit" }));
  await waitFor(() => expect(editor.value).toBe(replacement));
});

it("blocks brainstorm Append from destroying a standalone LaTeX document", async () => {
  const source = [
    "\\documentclass{article}",
    "\\begin{document}",
    "Name",
    "\\end{document}",
  ].join("\n");
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: source } });
  openChatWindow(editor);
  fireEvent.change(screen.getByLabelText("chatMessage"), {
    target: { value: "Gợi ý chỉnh sửa?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "sendMessage" }));
  expect(await screen.findByText("Thêm thí nghiệm thay đổi góc camera.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "appendToDocument" }));
  expect(screen.getByText("documentBrainstormLatexApplyBlocked")).toBeInTheDocument();
  expect(screen.getByLabelText("documentBody")).toHaveValue(source);
});

it("never offers Accept when a whole-source LaTeX rename returns explanatory prose", async () => {
  const source = [
    "\\documentclass{article}",
    "\\begin{document}",
    "\\textbf{NGUYỄN MINH AN}",
    "\\end{document}",
  ].join("\n");
  mocks.instantEdit.mockImplementationOnce(async (input) => ({
    source_revision: input.sourceRevision,
    selection_start: input.selectionStart,
    selection_end: input.selectionEnd,
    original_text_hash: "a".repeat(64),
    replacement_text: [
      'Tôi sẽ giúp bạn thay đổi tên trong CV từ "Nguyễn Minh An" thành "Bùi Hoàng Linh".',
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
  }));
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: source } });
  openChatWindow(editor);
  fireEvent.change(screen.getByLabelText("chatMessage"), {
    target: { value: "sửa tên thành Bùi Hoàng Linh" },
  });
  fireEvent.click(screen.getByRole("button", { name: "sendMessage" }));

  expect(await screen.findByText("instantEditInvalidResponse")).toBeInTheDocument();
  expect(await screen.findByText("documentChatEditFailed")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "acceptAiEdit" })).not.toBeInTheDocument();
  expect(editor.value).toBe(source);
});

it("keeps a timed-out brainstorm question and retries it without a duplicate user turn", async () => {
  mocks.brainstormDocument
    .mockRejectedValueOnce(new ApiError("DeepSeek chat request timed out", "CHAT_PROVIDER_UNAVAILABLE", 503))
    .mockResolvedValueOnce({
      content: "Đã xác định vị trí tên cần đổi.",
      provider_name: "deepseek",
      model_name: "deepseek-test",
      source_context_truncated: false,
    });
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: "Tên hiện tại: Nguyễn Minh An" } });
  openChatWindow(editor);
  fireEvent.change(screen.getByLabelText("chatMessage"), {
    target: { value: "Cần bổ sung thí nghiệm nào?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "sendMessage" }));

  expect(await screen.findByText("documentBrainstormTemporaryFailure")).toBeInTheDocument();
  expect(screen.getAllByText("Cần bổ sung thí nghiệm nào?")).toHaveLength(1);
  expect(mocks.brainstormDocument).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "retry" }));

  expect(await screen.findByText("Đã xác định vị trí tên cần đổi.")).toBeInTheDocument();
  expect(screen.getAllByText("Cần bổ sung thí nghiệm nào?")).toHaveLength(1);
  expect(mocks.brainstormDocument).toHaveBeenCalledTimes(2);
  expect(mocks.brainstormDocument.mock.calls[1][0]).toMatchObject({
    message: "Cần bổ sung thí nghiệm nào?",
    history: [],
  });
});

it("routes a selection action into the brainstorm chat panel instead of below the editor", async () => {
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: "Camera baseline." } });
  editor.setSelectionRange(0, 16);
  fireEvent.select(editor);

  fireEvent.click(screen.getByRole("button", { name: "aiEditAction.improve" }));

  expect(await screen.findByText("aiEditAction.improve")).toBeInTheDocument();
  const review = (await screen.findByText("instantEditReviewRequired")).closest("article");
  expect(review).toHaveTextContent("Camera baseline.");
  expect(review).toHaveTextContent("Clear camera baseline.");
  expect(screen.queryByText("instantEditReviewRequired")?.closest("article")
    ?.closest("aside")?.className ?? "").toContain("document-brainstorm");
  expect(editor.value).toBe("Camera baseline.");
});

it("reviews old and new authoring text before accepting it into the local draft", async () => {
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: "Camera baseline." } });
  editor.setSelectionRange(0, 16);
  fireEvent.select(editor);

  fireEvent.click(screen.getByRole("button", { name: "aiEditAction.improve" }));
  const review = (await screen.findByText("instantEditReviewRequired")).closest("article");
  expect(review).toHaveTextContent("Camera baseline.");
  expect(review).toHaveTextContent("Clear camera baseline.");
  expect(editor.value).toBe("Camera baseline.");
  fireEvent.click(screen.getByRole("button", { name: "acceptAiEdit" }));
  await waitFor(() => expect(editor.value).toBe("Clear camera baseline."));
  expect(screen.getByText(/instantEditApplied/)).toBeInTheDocument();
  expect(mocks.uploadDocument).not.toHaveBeenCalled();
  expect(readDocumentAuthorDraft(
    window.localStorage,
    documentDraftStorageKey("owner-one"),
  )?.content).toBe("Clear camera baseline.");
});

it("rejects a late AI patch after the user changes the draft", async () => {
  let resolvePatch: ((value: unknown) => void) | undefined;
  mocks.instantEdit.mockImplementation((input) => new Promise((resolve) => {
    resolvePatch = resolve;
    void input;
  }));
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: "Camera baseline." } });
  editor.setSelectionRange(0, 16);
  fireEvent.select(editor);
  mocks.instantEdit.mockClear();
  fireEvent.click(screen.getByRole("button", { name: "aiEditAction.improve" }));
  await waitFor(() => expect(mocks.instantEdit).toHaveBeenCalledOnce());
  fireEvent.change(editor, { target: { value: "User changed the draft." } });
  const input = mocks.instantEdit.mock.calls[0][0];
  resolvePatch?.({
    source_revision: input.sourceRevision,
    selection_start: input.selectionStart,
    selection_end: input.selectionEnd,
    original_text_hash: "a".repeat(64),
    replacement_text: "Late AI replacement.",
    explanation: "Late response.",
    risk: "low",
    auto_apply_allowed: true,
    warnings: [],
    provider_name: "deepseek",
    model_name: "deepseek-test",
  });

  expect(await screen.findByText("instantEditStale")).toBeInTheDocument();
  expect(editor.value).toBe("User changed the draft.");
});

it("rejects a reviewed AI change without modifying the authoring draft", async () => {
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: "Camera baseline." } });
  editor.setSelectionRange(0, 16);
  fireEvent.select(editor);

  fireEvent.click(screen.getByRole("button", { name: "aiEditAction.improve" }));
  expect(await screen.findByText("instantEditReviewRequired")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "rejectAiEdit" }));

  expect(editor.value).toBe("Camera baseline.");
  expect(screen.queryByText("instantEditReviewRequired")).not.toBeInTheDocument();
});

it("offers an explicit retry after a transient proxy failure", async () => {
  mocks.instantEdit.mockRejectedValueOnce(
    new ApiError("Request failed (500)", "request_error", 500),
  );
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: "Camera baseline." } });
  editor.setSelectionRange(0, 16);
  fireEvent.select(editor);

  fireEvent.click(screen.getByRole("button", { name: "aiEditAction.improve" }));
  expect(await screen.findByText("instantEditTemporaryFailure")).toBeInTheDocument();
  const callsBeforeRetry = mocks.instantEdit.mock.calls.length;
  fireEvent.click(screen.getByRole("button", { name: "retry" }));

  expect(await screen.findByText("instantEditReviewRequired")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "acceptAiEdit" }));
  await waitFor(() => expect(editor.value).toBe("Clear camera baseline."));
  expect(mocks.instantEdit).toHaveBeenCalledTimes(callsBeforeRetry + 1);
});

it("keeps source preview collapsed until the user requests it", () => {
  render(<DocumentAuthoring userId="owner-one" />);
  fireEvent.change(screen.getByLabelText("documentBody"), {
    target: { value: "# Camera baseline" },
  });

  const disclosure = screen.getByText("previewDocument").closest("details");
  expect(disclosure).not.toHaveAttribute("open");
  fireEvent.click(screen.getByText("previewDocument"));
  expect(disclosure).toHaveAttribute("open");
});

it("opens the two-pane edit window on a selection option and keeps edits after closing", async () => {
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: "Camera baseline." } });
  editor.setSelectionRange(0, 16);
  fireEvent.select(editor);

  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "aiEditAction.improve" }));
  const dialog = await screen.findByRole("dialog");
  expect(dialog).toBeInTheDocument();
  const windowEditor = screen.getByRole("textbox", {
    name: "documentWindowBody",
  }) as HTMLTextAreaElement;
  expect(screen.getByLabelText("documentWindowChat")).toBeInTheDocument();

  fireEvent.change(windowEditor, { target: { value: "Camera baseline.\n\nEdited in window." } });
  fireEvent.click(screen.getByRole("button", { name: "closeFocusWindow" }));

  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByLabelText("documentBody")).toHaveValue(
    "Camera baseline.\n\nEdited in window.",
  );
});

it("shows selection options again after closing the window with a pending review", async () => {
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: "Camera baseline." } });
  editor.setSelectionRange(0, 16);
  fireEvent.select(editor);

  fireEvent.click(screen.getByRole("button", { name: "aiEditAction.improve" }));
  expect(await screen.findByText("instantEditReviewRequired")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "closeFocusWindow" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

  editor.setSelectionRange(0, 16);
  fireEvent.select(editor);
  expect(await screen.findByRole("button", { name: "aiEditAction.improve" })).toBeInTheDocument();
});

it("persists chat history per document and lists it in the chat window", async () => {
  render(<DocumentAuthoring userId="owner-one" />);
  const editor = screen.getByLabelText("documentBody") as HTMLTextAreaElement;
  fireEvent.change(editor, { target: { value: "Camera baseline." } });
  openChatWindow(editor);
  fireEvent.change(screen.getByLabelText("chatMessage"), {
    target: { value: "Cần thêm thí nghiệm gì?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "sendMessage" }));
  expect(await screen.findByText("Thêm thí nghiệm thay đổi góc camera.")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "closeFocusWindow" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

  openChatWindow(screen.getByLabelText("documentBody") as HTMLTextAreaElement);
  const dialog = await screen.findByRole("dialog");
  expect(dialog).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "chatHistory" }));
  expect(screen.getAllByText("Cần thêm thí nghiệm gì?")).toHaveLength(2);
});
