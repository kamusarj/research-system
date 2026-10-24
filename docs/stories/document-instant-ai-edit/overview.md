# Instant AI Edit in Document Drafts

## Current Behavior

Document brainstorm returns free-form Markdown and requires a later Replace/Insert/Append click.
Uploaded-document selection actions create a durable proposal and require Accept before the source
changes. A brainstorm response is not bound to the exact editor revision that produced it, so a
late response could be applied against a newer selection or source.

## Target Behavior

Owners and researchers can select source text and choose Improve, Shorten, Expand, Fix grammar or
a custom instruction. The provider returns one typed replacement patch bound to the current local
source revision, target range and original-text hash. Low/medium-risk patches replace that range in
the cached local draft immediately, highlight the replacement and expose Undo/View diff. If source,
range or selected text changed while the request was in flight, nothing is applied.

Selections containing protected facts, citations, URLs, code or formula syntax remain review-only.
No instant edit creates a source version, saves the document, refreshes RAG or publishes graph data;
the existing explicit Create/Save action remains authoritative.

## Affected Users

- Owners and researchers editing supported UTF-8 source documents.
- Viewers remain read-only and cannot request or apply edits.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-unified-editor-chat/`
- `docs/stories/document-ai-edit-rag/`
- `docs/decisions/0026-stateless-document-editor-brainstorm.md`

## Non-Goals

- No automatic canonical Save, version creation, RAG rebuild or graph publication.
- No lossy PDF/DOCX editing.
- No autonomous fact correction or citation invention.
- No collaborative rebase/merge across browsers.
