import { api, apiFetch, ApiError, vietnameseApiErrorMessage } from "@/lib/api";
import type {
  DocumentAIEdit,
  DocumentBrainstormMessage,
  DocumentBrainstormResponse,
  DocumentInstantEditAction,
  DocumentInstantEditPatch,
  DocumentGraphResearchResult,
  DocumentRagStatus,
  DocumentSourceVersion,
  DocumentWorkspace,
} from "@/lib/types";

export const DOCUMENT_MAX_UPLOAD_BYTES = 20_000_000;
export const DOCUMENT_AUTHOR_DRAFT_MAX_CHARS = 2_000_000;
const DOCUMENT_AUTHOR_DRAFT_VERSION = 1 as const;
const DOCUMENT_EDITOR_DRAFT_VERSION = 1 as const;

export async function deleteDocument(workspaceId: string): Promise<void> {
  await api<void>(`/documents/${workspaceId}`, { method: "DELETE" });
}

export function researchDocumentGraph(
  workspaceId: string,
  options: { nodeIds?: string[]; createChangeSet?: boolean } = {},
): Promise<DocumentGraphResearchResult> {
  return api(`/documents/${workspaceId}/graph/research`, {
    method: "POST",
    body: JSON.stringify({
      node_ids: options.nodeIds ?? [],
      create_change_set: options.createChangeSet ?? false,
    }),
  });
}

export const DOCUMENT_AUTHORING_FORMATS = [
  {
    value: "markdown",
    extension: ".md",
    mimeType: "text/markdown",
    previewKind: "markdown",
  },
  {
    value: "text",
    extension: ".txt",
    mimeType: "text/plain",
    previewKind: "plain",
  },
  {
    value: "latex",
    extension: ".tex",
    mimeType: "application/x-tex",
    previewKind: "latex",
  },
  {
    value: "rst",
    extension: ".rst",
    mimeType: "text/x-rst",
    previewKind: "markup",
  },
  {
    value: "asciidoc",
    extension: ".adoc",
    mimeType: "text/asciidoc",
    previewKind: "markup",
  },
  {
    value: "html",
    extension: ".html",
    mimeType: "text/html",
    previewKind: "html",
  },
] as const;

export type DocumentAuthoringFormat = (typeof DOCUMENT_AUTHORING_FORMATS)[number]["value"];

export const DOCUMENT_EDITABLE_IMPORT_ACCEPT =
  ".txt,.md,.markdown,.tex,.latex,.rst,.adoc,.asciidoc,.html,.htm,text/plain,text/markdown,application/x-tex,text/x-tex,text/asciidoc,text/html";

export type DocumentAuthorDraft = {
  version: typeof DOCUMENT_AUTHOR_DRAFT_VERSION;
  title: string;
  format: DocumentAuthoringFormat;
  content: string;
  updatedAt: string;
};

type DraftStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export type DocumentEditorDraft = {
  version: typeof DOCUMENT_EDITOR_DRAFT_VERSION;
  content: string;
  updatedAt: string;
};

export function emptyDocumentAuthorDraft(): DocumentAuthorDraft {
  return {
    version: DOCUMENT_AUTHOR_DRAFT_VERSION,
    title: "",
    format: "markdown",
    content: "",
    updatedAt: "",
  };
}

export function documentDraftStorageKey(userId: string): string {
  return `research-system:document-author-draft:v1:${encodeURIComponent(userId)}`;
}

export function readDocumentAuthorDraft(
  storage: DraftStorage,
  key: string,
): DocumentAuthorDraft | null {
  try {
    const raw = storage.getItem(key);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<DocumentAuthorDraft>;
    const validFormat = DOCUMENT_AUTHORING_FORMATS.some(
      (format) => format.value === value.format,
    );
    if (
      value.version !== DOCUMENT_AUTHOR_DRAFT_VERSION
      || typeof value.title !== "string"
      || typeof value.content !== "string"
      || typeof value.updatedAt !== "string"
      || !validFormat
      || value.title.length > 180
      || value.content.length > DOCUMENT_AUTHOR_DRAFT_MAX_CHARS
    ) {
      return null;
    }
    return value as DocumentAuthorDraft;
  } catch {
    return null;
  }
}

export function writeDocumentAuthorDraft(
  storage: DraftStorage,
  key: string,
  draft: DocumentAuthorDraft,
): boolean {
  if (draft.title.length > 180 || draft.content.length > DOCUMENT_AUTHOR_DRAFT_MAX_CHARS) {
    return false;
  }
  try {
    storage.setItem(key, JSON.stringify(draft));
    return true;
  } catch {
    return false;
  }
}

export function clearDocumentAuthorDraft(storage: DraftStorage, key: string): void {
  try {
    storage.removeItem(key);
  } catch {
    // A disabled browser storage backend is already reported by write failures.
  }
}

export function documentEditorDraftStorageKey(
  userId: string,
  workspaceId: string,
  sourceVersion: number,
): string {
  return `research-system:document-editor-draft:v1:${encodeURIComponent(userId)}:${encodeURIComponent(workspaceId)}:${sourceVersion}`;
}

export function readDocumentEditorDraft(
  storage: DraftStorage,
  key: string,
): DocumentEditorDraft | null {
  try {
    const raw = storage.getItem(key);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<DocumentEditorDraft>;
    if (
      value.version !== DOCUMENT_EDITOR_DRAFT_VERSION
      || typeof value.content !== "string"
      || typeof value.updatedAt !== "string"
      || value.content.length > DOCUMENT_AUTHOR_DRAFT_MAX_CHARS
    ) return null;
    return value as DocumentEditorDraft;
  } catch {
    return null;
  }
}

export function writeDocumentEditorDraft(
  storage: DraftStorage,
  key: string,
  content: string,
): boolean {
  if (content.length > DOCUMENT_AUTHOR_DRAFT_MAX_CHARS) return false;
  try {
    storage.setItem(key, JSON.stringify({
      version: DOCUMENT_EDITOR_DRAFT_VERSION,
      content,
      updatedAt: new Date().toISOString(),
    } satisfies DocumentEditorDraft));
    return true;
  } catch {
    return false;
  }
}

export function clearDocumentEditorDraft(storage: DraftStorage, key: string): void {
  clearDocumentAuthorDraft(storage, key);
}

export function documentAuthoringFormat(format: DocumentAuthoringFormat) {
  return DOCUMENT_AUTHORING_FORMATS.find((option) => option.value === format)
    ?? DOCUMENT_AUTHORING_FORMATS[0];
}

export function documentAuthoringFormatFromFilename(
  filename: string,
): DocumentAuthoringFormat | null {
  const normalized = filename.trim().toLocaleLowerCase();
  const match = DOCUMENT_AUTHORING_FORMATS.find((option) => {
    if (normalized.endsWith(option.extension)) return true;
    if (option.value === "markdown") return normalized.endsWith(".markdown");
    if (option.value === "latex") return normalized.endsWith(".latex");
    if (option.value === "asciidoc") return normalized.endsWith(".asciidoc");
    if (option.value === "html") return normalized.endsWith(".htm");
    return false;
  });
  return match?.value ?? null;
}

function readFileBytes(file: File): Promise<ArrayBuffer> {
  if (typeof file.arrayBuffer === "function") return file.arrayBuffer();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error("Không thể đọc tệp đã chọn"));
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.readAsArrayBuffer(file);
  });
}

export async function editableDocumentDraftFromFile(
  file: File,
): Promise<Pick<DocumentAuthorDraft, "title" | "format" | "content">> {
  if (file.size > DOCUMENT_MAX_UPLOAD_BYTES) {
    throw new Error("DOCUMENT_TOO_LARGE");
  }
  const format = documentAuthoringFormatFromFilename(file.name);
  if (!format) throw new Error("DOCUMENT_NOT_EDITABLE_SOURCE");
  let content: string;
  try {
    content = new TextDecoder("utf-8", { fatal: true })
      .decode(await readFileBytes(file))
      .replace(/\r\n/g, "\n")
      .replace(/\r/g, "\n");
  } catch {
    throw new Error("DOCUMENT_INVALID_UTF8");
  }
  if (!content.trim()) throw new Error("DOCUMENT_EMPTY");
  if (content.length > DOCUMENT_AUTHOR_DRAFT_MAX_CHARS) {
    throw new Error("DOCUMENT_DRAFT_TOO_LARGE");
  }
  const suffixPattern = /\.(?:md|markdown|txt|tex|latex|rst|adoc|asciidoc|html|htm)$/i;
  return {
    title: file.name.replace(suffixPattern, "").slice(0, 180),
    format,
    content,
  };
}

export function authoredDocumentFile(draft: DocumentAuthorDraft): File {
  const format = documentAuthoringFormat(draft.format);
  const knownSuffixes = DOCUMENT_AUTHORING_FORMATS
    .map((option) => option.extension.replace(".", "\\."))
    .join("|");
  const stem = draft.title
    .trim()
    .replace(new RegExp(`(?:${knownSuffixes})$`, "i"), "")
    .replace(/[\\/:*?"<>|\u0000-\u001f]/g, "-")
    .replace(/\s+/g, " ")
    .replace(/-+/g, "-")
    .replace(/^[.\s-]+|[.\s-]+$/g, "")
    .slice(0, 180);
  if (!stem) throw new Error("Cần nhập tiêu đề tài liệu");
  return new File([draft.content], `${stem}${format.extension}`, {
    type: format.mimeType,
    lastModified: Date.now(),
  });
}

export async function uploadDocument(file: File): Promise<DocumentWorkspace> {
  const body = new FormData();
  body.set("file", file);
  const response = await apiFetch("/documents", { method: "POST", body });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as
      | { error?: { code?: string; message?: string } }
      | null;
    throw new ApiError(
      vietnameseApiErrorMessage(payload?.error?.code, response.status),
      payload?.error?.code ?? "request_error",
      response.status,
    );
  }
  return response.json() as Promise<DocumentWorkspace>;
}

export async function queueDocument(
  workspaceId: string,
  action: "analyze" | "retry" = "analyze",
): Promise<DocumentWorkspace> {
  const response = await apiFetch(`/documents/${workspaceId}/${action}`, {
    method: "POST",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as
      | { error?: { code?: string; message?: string } }
      | null;
    throw new ApiError(
      vietnameseApiErrorMessage(payload?.error?.code, response.status),
      payload?.error?.code ?? "request_error",
      response.status,
    );
  }
  return response.json() as Promise<DocumentWorkspace>;
}

export async function saveDocumentSource(
  workspaceId: string,
  baseVersion: number,
  content: string,
  changeSummary?: string,
): Promise<DocumentSourceVersion> {
  return apiFetchJson<DocumentSourceVersion>(`/documents/${workspaceId}/versions`, {
    method: "POST",
    body: JSON.stringify({
      base_version: baseVersion,
      content,
      change_summary: changeSummary || null,
    }),
  });
}

export async function requestDocumentAIEdit(
  workspaceId: string,
  input: {
    baseVersion: number;
    selectionStart: number;
    selectionEnd: number;
    action: "improve" | "shorten" | "expand" | "fix_grammar" | "custom";
    instruction?: string;
  },
): Promise<DocumentAIEdit> {
  return apiFetchJson<DocumentAIEdit>(`/documents/${workspaceId}/ai-edits`, {
    method: "POST",
    body: JSON.stringify({
      base_version: input.baseVersion,
      selection_start: input.selectionStart,
      selection_end: input.selectionEnd,
      action: input.action,
      instruction: input.instruction || null,
    }),
  });
}

export async function reviewDocumentAIEdit(
  workspaceId: string,
  proposalId: string,
  decision: "accept" | "reject",
): Promise<DocumentAIEdit> {
  return apiFetchJson<DocumentAIEdit>(
    `/documents/${workspaceId}/ai-edits/${proposalId}/${decision}`,
    { method: "POST" },
  );
}

export async function restoreDocumentSource(
  workspaceId: string,
  versionNumber: number,
  baseVersion: number,
): Promise<DocumentSourceVersion> {
  return apiFetchJson<DocumentSourceVersion>(
    `/documents/${workspaceId}/versions/${versionNumber}/restore`,
    { method: "POST", body: JSON.stringify({ base_version: baseVersion }) },
  );
}

export async function rebuildDocumentRag(workspaceId: string): Promise<DocumentRagStatus> {
  return apiFetchJson<DocumentRagStatus>(`/documents/${workspaceId}/rag/rebuild`, {
    method: "POST",
  });
}

export async function brainstormDocument(input: {
  source: string;
  message: string;
  history: DocumentBrainstormMessage[];
  selection?: { start: number; end: number } | null;
}): Promise<DocumentBrainstormResponse> {
  return apiFetchJson<DocumentBrainstormResponse>("/documents/brainstorm", {
    method: "POST",
    body: JSON.stringify({
      source: input.source,
      message: input.message,
      history: input.history.slice(-10),
      selection_start: input.selection?.start ?? null,
      selection_end: input.selection?.end ?? null,
    }),
  });
}

export async function requestDocumentInstantEdit(input: {
  source: string;
  sourceRevision: string;
  selectionStart: number;
  selectionEnd: number;
  action: DocumentInstantEditAction;
  instruction?: string;
  sourceFormat?: string;
}): Promise<DocumentInstantEditPatch> {
  return apiFetchJson<DocumentInstantEditPatch>("/documents/edit-in-place", {
    method: "POST",
    body: JSON.stringify({
      source: input.source,
      source_revision: input.sourceRevision,
      selection_start: input.selectionStart,
      selection_end: input.selectionEnd,
      action: input.action,
      instruction: input.instruction || null,
      source_format: input.sourceFormat || null,
    }),
  });
}

async function apiFetchJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await apiFetch(path, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as
      | { error?: { code?: string; message?: string } }
      | null;
    throw new ApiError(
      vietnameseApiErrorMessage(payload?.error?.code, response.status),
      payload?.error?.code ?? "request_error",
      response.status,
    );
  }
  return response.json() as Promise<T>;
}

export function formatDocumentBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
