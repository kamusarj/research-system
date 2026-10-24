import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import DocumentsPage from "./page";

const mocks = vi.hoisted(() => ({
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  refetch: vi.fn(),
  items: [] as Array<Record<string, unknown>>,
}));

vi.mock("@tanstack/react-query", () => ({
  useQuery: () => ({
    data: { items: mocks.items, total: mocks.items.length },
    isLoading: false,
    error: null,
    refetch: mocks.refetch,
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/documents")>("@/lib/documents");
  return {
    ...actual,
    uploadDocument: mocks.uploadDocument,
    deleteDocument: mocks.deleteDocument,
  };
});

beforeEach(() => {
  window.localStorage.clear();
  mocks.items.length = 0;
  mocks.uploadDocument.mockReset();
  mocks.uploadDocument.mockResolvedValue({ id: "workspace" });
  mocks.deleteDocument.mockReset();
  mocks.deleteDocument.mockResolvedValue(undefined);
  mocks.refetch.mockReset();
  mocks.refetch.mockResolvedValue(undefined);
});

it("links an uploaded filename and primary action to its document workspace", () => {
  mocks.items.push({
    id: "workspace-1",
    research_id: "research-1",
    filename: "agent-memory.pdf",
    summary: "A concise account of governed agent memory.",
    size_bytes: 42,
    content_hash: "a".repeat(64),
    processing_status: "needs_review",
    updated_at: "2026-08-09T08:00:00Z",
  });

  render(<DocumentsPage />);

  expect(screen.getByRole("link", { name: "agent-memory.pdf" })).toHaveAttribute(
    "href",
    "/documents/workspace-1",
  );
  expect(screen.getByText("A concise account of governed agent memory.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "editDocument" })).toHaveAttribute(
    "href",
    "/documents/workspace-1",
  );
  expect(screen.getByRole("link", { name: "viewAnalysis" })).toHaveAttribute(
    "href",
    "/documents/workspace-1#document-analysis",
  );
  expect(screen.queryByText("status")).not.toBeInTheDocument();
  expect(screen.queryByText("updated")).not.toBeInTheDocument();
});

it("confirms owner deletion and refreshes the document list", async () => {
  mocks.items.push({
    id: "workspace-1",
    research_id: "research-1",
    filename: "agent-memory.pdf",
    summary: "Governed memory.",
    size_bytes: 42,
    content_hash: "a".repeat(64),
    processing_status: "needs_review",
    updated_at: "2026-08-09T08:00:00Z",
  });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);

  render(<DocumentsPage />);
  fireEvent.click(screen.getByRole("button", { name: "deleteDocument" }));

  await waitFor(() => expect(mocks.deleteDocument).toHaveBeenCalledWith("workspace-1"));
  expect(confirm).toHaveBeenCalledWith(
    "confirmDeleteDocument".replace("{filename}", "agent-memory.pdf"),
  );
  expect(await screen.findByText("documentDeleted")).toBeInTheDocument();
  expect(mocks.refetch).toHaveBeenCalledOnce();
  confirm.mockRestore();
});

it("uploads a supported document and refreshes the workspace list", async () => {
  render(<DocumentsPage />);
  const file = new File(["%PDF-1.4\n%%EOF"], "agent-memory.pdf", { type: "application/pdf" });

  fireEvent.change(screen.getByLabelText("chooseFile"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "uploadDocument" }));

  await waitFor(() => expect(mocks.uploadDocument).toHaveBeenCalledWith(file));
  expect(await screen.findByText("documentUploaded")).toBeInTheDocument();
  expect(mocks.refetch).toHaveBeenCalledOnce();
});

it("advertises the bounded editable document formats", () => {
  render(<DocumentsPage />);

  const binaryInput = screen.getByLabelText("chooseFile");
  expect(binaryInput).toHaveAttribute("accept", expect.stringContaining(".docx"));
  expect(binaryInput).not.toHaveAttribute("accept", expect.stringContaining(".tex"));
  const editableInput = screen.getByLabelText("importEditableSource");
  expect(editableInput).toHaveAttribute("accept", expect.stringContaining(".tex"));
  expect(editableInput).toHaveAttribute("accept", expect.stringContaining(".markdown"));
  expect(editableInput).toHaveAttribute("accept", expect.stringContaining(".adoc"));
});
