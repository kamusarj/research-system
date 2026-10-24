import { describe, expect, it } from "vitest";
import {
  applyDocumentInstantPatch,
  documentSourceRevision,
  isStandaloneLatexDocument,
  normalizeDocumentSelection,
  paragraphRangeAtCursor,
  snapshotDocumentSelection,
  undoDocumentInstantPatch,
} from "./document-instant-edit";

function patch(sourceRevision: string) {
  return {
    source_revision: sourceRevision,
    selection_start: 6,
    selection_end: 14,
    original_text_hash: "a".repeat(64),
    replacement_text: "clear text.",
    explanation: "Improved clarity.",
    risk: "low" as const,
    auto_apply_allowed: true,
    warnings: [],
    provider_name: "deepseek",
    model_name: "test",
  };
}

describe("document instant edits", () => {
  it("applies an anchored patch and undoes only the replacement range", () => {
    const source = "Start unclear. End";
    const snapshot = snapshotDocumentSelection(source, { start: 6, end: 14 });
    expect(snapshot).not.toBeNull();

    const applied = applyDocumentInstantPatch(source, snapshot!, patch(snapshot!.sourceRevision));
    expect(applied.ok).toBe(true);
    if (!applied.ok) return;
    expect(applied.source).toBe("Start clear text. End");

    const undone = undoDocumentInstantPatch(`Prefix ${applied.source}`, {
      ...applied.change,
      start: applied.change.start + 7,
    });
    expect(undone).toEqual({ ok: true, source: "Prefix Start unclear. End" });
  });

  it("rejects the response when any source text changed while AI was running", () => {
    const source = "Start unclear. End";
    const snapshot = snapshotDocumentSelection(source, { start: 6, end: 14 })!;
    const result = applyDocumentInstantPatch(
      `${source} changed`,
      snapshot,
      patch(snapshot.sourceRevision),
    );

    expect(result).toEqual({ ok: false, reason: "stale" });
    expect(documentSourceRevision(source)).not.toBe(documentSourceRevision(`${source} changed`));
  });

  it("targets the paragraph containing the cursor", () => {
    expect(paragraphRangeAtCursor("First paragraph.\n\nSecond paragraph.", 24)).toEqual({
      start: 18,
      end: 35,
    });
  });

  it("drops stale selections that no longer fit the source", () => {
    expect(normalizeDocumentSelection("short", { start: 0, end: 20 })).toBeNull();
    expect(normalizeDocumentSelection("short", { start: 1, end: 1 })).toBeNull();
    expect(normalizeDocumentSelection("short", { start: 0, end: 5 })).toEqual({
      start: 0,
      end: 5,
    });
    expect(normalizeDocumentSelection("   ", { start: 0, end: 3 })).toBeNull();
  });

  it("rejects explanatory prose as a whole-source LaTeX replacement", () => {
    const source = [
      "\\documentclass{article}",
      "\\begin{document}",
      "\\textbf{NGUYỄN MINH AN}",
      "\\end{document}",
    ].join("\n");
    const snapshot = snapshotDocumentSelection(source, { start: 0, end: source.length })!;
    const malformedPatch = {
      ...patch(snapshot.sourceRevision),
      selection_start: 0,
      selection_end: source.length,
      replacement_text: [
        "Tôi sẽ giúp bạn thay đổi tên trong CV.",
        "```latex",
        "\\textbf{BÙI HOÀNG LINH}",
        "```",
      ].join("\n"),
    };

    expect(applyDocumentInstantPatch(source, snapshot, malformedPatch)).toEqual({
      ok: false,
      reason: "format",
    });
    expect(isStandaloneLatexDocument(malformedPatch.replacement_text)).toBe(false);
  });

  it("allows a complete renamed LaTeX document through to review/application", () => {
    const source = [
      "% !TeX program = xelatex",
      "\\documentclass{article}",
      "\\begin{document}",
      "\\textbf{NGUYỄN MINH AN}",
      "\\end{document}",
    ].join("\n");
    const replacement = source.replace("NGUYỄN MINH AN", "BÙI HOÀNG LINH");
    const snapshot = snapshotDocumentSelection(source, { start: 0, end: source.length })!;
    const validPatch = {
      ...patch(snapshot.sourceRevision),
      selection_start: 0,
      selection_end: source.length,
      replacement_text: replacement,
    };

    const result = applyDocumentInstantPatch(source, snapshot, validPatch);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.source).toBe(replacement);
  });
});
