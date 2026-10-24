import type { DocumentInstantEditPatch } from "@/lib/types";

export type DocumentEditRange = { start: number; end: number };

export type DocumentInstantEditSnapshot = {
  sourceRevision: string;
  range: DocumentEditRange;
  originalText: string;
};

export type AppliedDocumentInstantEdit = {
  start: number;
  originalText: string;
  replacementText: string;
  explanation: string;
  risk: DocumentInstantEditPatch["risk"];
  warnings: string[];
  providerName: string;
  modelName: string;
};

export type DocumentPatchResult =
  | { ok: true; source: string; change: AppliedDocumentInstantEdit }
  | { ok: false; reason: "stale" | "invalid" | "format" };

const LATEX_DOCUMENTCLASS = "\\documentclass";
const LATEX_DOCUMENT_BEGIN = "\\begin{document}";
const LATEX_DOCUMENT_END = "\\end{document}";

function onlyWhitespaceOrLatexComments(value: string): boolean {
  return value.split(/\r?\n/).every((line) => !line.trim() || line.trimStart().startsWith("%"));
}

export function isStandaloneLatexDocument(value: string): boolean {
  if (value.includes("```")) return false;
  const documentclass = value.indexOf(LATEX_DOCUMENTCLASS);
  const documentBegin = value.indexOf(LATEX_DOCUMENT_BEGIN, documentclass + 1);
  const documentEnd = value.indexOf(LATEX_DOCUMENT_END, documentBegin + 1);
  if (documentclass < 0 || documentBegin < 0 || documentEnd < 0) return false;
  if (value.indexOf(LATEX_DOCUMENT_END, documentEnd + LATEX_DOCUMENT_END.length) >= 0) return false;
  const prefix = value.slice(0, documentclass).replace(/^\uFEFF/, "");
  const suffix = value.slice(documentEnd + LATEX_DOCUMENT_END.length);
  return onlyWhitespaceOrLatexComments(prefix) && onlyWhitespaceOrLatexComments(suffix);
}

export function patchPreservesDocumentStructure(
  source: string,
  snapshot: DocumentInstantEditSnapshot,
  replacement: string,
): boolean {
  const selectsCompleteSource = snapshot.range.start === 0 && snapshot.range.end === source.length;
  if (!selectsCompleteSource || !isStandaloneLatexDocument(snapshot.originalText)) return true;
  return isStandaloneLatexDocument(replacement);
}

export function documentSourceRevision(source: string): string {
  let hash = 0x811c9dc5;
  for (let index = 0; index < source.length; index += 1) {
    hash ^= source.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return `draft-${source.length}-${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

export function normalizeDocumentSelection(
  source: string,
  range: DocumentEditRange | null | undefined,
): DocumentEditRange | null {
  if (!range) return null;
  if (range.start < 0 || range.end <= range.start || range.end > source.length) return null;
  if (!source.slice(range.start, range.end).trim()) return null;
  return range;
}

export function snapshotDocumentSelection(
  source: string,
  range: DocumentEditRange,
): DocumentInstantEditSnapshot | null {
  const valid = normalizeDocumentSelection(source, range);
  if (!valid) return null;
  return {
    sourceRevision: documentSourceRevision(source),
    range: valid,
    originalText: source.slice(valid.start, valid.end),
  };
}

export function applyDocumentInstantPatch(
  source: string,
  snapshot: DocumentInstantEditSnapshot,
  patch: DocumentInstantEditPatch,
): DocumentPatchResult {
  if (
    patch.source_revision !== snapshot.sourceRevision
    || patch.selection_start !== snapshot.range.start
    || patch.selection_end !== snapshot.range.end
    || patch.selection_end > source.length
    || !patch.replacement_text
  ) return { ok: false, reason: "invalid" };
  if (!patchPreservesDocumentStructure(source, snapshot, patch.replacement_text)) {
    return { ok: false, reason: "format" };
  }
  if (
    documentSourceRevision(source) !== snapshot.sourceRevision
    || source.slice(snapshot.range.start, snapshot.range.end) !== snapshot.originalText
  ) return { ok: false, reason: "stale" };
  return {
    ok: true,
    source: source.slice(0, snapshot.range.start)
      + patch.replacement_text
      + source.slice(snapshot.range.end),
    change: {
      start: snapshot.range.start,
      originalText: snapshot.originalText,
      replacementText: patch.replacement_text,
      explanation: patch.explanation,
      risk: patch.risk,
      warnings: patch.warnings,
      providerName: patch.provider_name,
      modelName: patch.model_name,
    },
  };
}

export function undoDocumentInstantPatch(
  source: string,
  change: AppliedDocumentInstantEdit,
): { ok: true; source: string } | { ok: false; reason: "stale" } {
  const end = change.start + change.replacementText.length;
  if (source.slice(change.start, end) !== change.replacementText) {
    return { ok: false, reason: "stale" };
  }
  return {
    ok: true,
    source: source.slice(0, change.start) + change.originalText + source.slice(end),
  };
}

export function paragraphRangeAtCursor(source: string, cursor: number): DocumentEditRange | null {
  if (!source.length) return null;
  const bounded = Math.max(0, Math.min(cursor, source.length));
  const startBreak = source.lastIndexOf("\n\n", Math.max(0, bounded - 1));
  const endBreak = source.indexOf("\n\n", bounded);
  const start = startBreak < 0 ? 0 : startBreak + 2;
  const end = endBreak < 0 ? source.length : endBreak;
  return source.slice(start, end).trim() ? { start, end } : null;
}
