import { beforeEach, expect, it } from "vitest";
import {
  DOCUMENT_AUTHOR_DRAFT_MAX_CHARS,
  authoredDocumentFile,
  clearDocumentAuthorDraft,
  documentDraftStorageKey,
  documentEditorDraftStorageKey,
  documentAuthoringFormatFromFilename,
  editableDocumentDraftFromFile,
  emptyDocumentAuthorDraft,
  formatDocumentBytes,
  readDocumentAuthorDraft,
  readDocumentEditorDraft,
  writeDocumentAuthorDraft,
  writeDocumentEditorDraft,
} from "./documents";

beforeEach(() => {
  window.localStorage.clear();
});

it("formats bounded document sizes for the upload workspace", () => {
  expect(formatDocumentBytes(512)).toBe("512 B");
  expect(formatDocumentBytes(1536)).toBe("1.5 KB");
  expect(formatDocumentBytes(2 * 1024 * 1024)).toBe("2.0 MB");
});

it("stores versioned author drafts under identity-scoped keys", () => {
  const ownerKey = documentDraftStorageKey("owner/one");
  const researcherKey = documentDraftStorageKey("researcher-two");
  const draft = {
    ...emptyDocumentAuthorDraft(),
    title: "Governed agents",
    content: "# Evidence\n\nHuman review is required.",
    updatedAt: "2026-07-30T15:00:00.000Z",
  };

  expect(writeDocumentAuthorDraft(window.localStorage, ownerKey, draft)).toBe(true);
  expect(readDocumentAuthorDraft(window.localStorage, ownerKey)).toEqual(draft);
  expect(readDocumentAuthorDraft(window.localStorage, researcherKey)).toBeNull();

  clearDocumentAuthorDraft(window.localStorage, ownerKey);
  expect(readDocumentAuthorDraft(window.localStorage, ownerKey)).toBeNull();
});

it("rejects corrupt and oversized authoring cache values", () => {
  const key = documentDraftStorageKey("local-user");
  window.localStorage.setItem(key, "{not-json");
  expect(readDocumentAuthorDraft(window.localStorage, key)).toBeNull();

  const oversized = {
    ...emptyDocumentAuthorDraft(),
    content: "x".repeat(DOCUMENT_AUTHOR_DRAFT_MAX_CHARS + 1),
    updatedAt: "2026-07-30T15:00:00.000Z",
  };
  expect(writeDocumentAuthorDraft(window.localStorage, key, oversized)).toBe(false);
});

it("turns an authored draft into a safe editable source file", () => {
  const file = authoredDocumentFile({
    ...emptyDocumentAuthorDraft(),
    title: "../Agent: governance.md",
    format: "latex",
    content: "\\section{Governance}\nHuman review.",
    updatedAt: "2026-07-30T15:00:00.000Z",
  });

  expect(file.name).toBe("Agent- governance.tex");
  expect(file.type).toBe("application/x-tex");
  expect(file.size).toBe(new Blob(["\\section{Governance}\nHuman review."]).size);
});

it("maps and imports UTF-8 editable source before document creation", async () => {
  expect(documentAuthoringFormatFromFilename("experiment.latex")).toBe("latex");
  expect(documentAuthoringFormatFromFilename("notes.asciidoc")).toBe("asciidoc");
  expect(documentAuthoringFormatFromFilename("binary.docx")).toBeNull();

  const imported = await editableDocumentDraftFromFile(new File(
    ["\\section{Robot}\r\nHuman-reviewed control."],
    "robot-study.tex",
    { type: "application/x-tex" },
  ));
  expect(imported).toEqual({
    title: "robot-study",
    format: "latex",
    content: "\\section{Robot}\nHuman-reviewed control.",
  });
});

it("scopes refresh-safe editor drafts by user, workspace and source version", () => {
  const key = documentEditorDraftStorageKey("owner/one", "workspace/one", 3);
  const nextVersion = documentEditorDraftStorageKey("owner/one", "workspace/one", 4);

  expect(writeDocumentEditorDraft(window.localStorage, key, "Unsaved source edit")).toBe(true);
  expect(readDocumentEditorDraft(window.localStorage, key)?.content).toBe(
    "Unsaved source edit",
  );
  expect(readDocumentEditorDraft(window.localStorage, nextVersion)).toBeNull();
});
