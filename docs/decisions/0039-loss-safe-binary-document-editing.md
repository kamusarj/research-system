# 0039 Loss-Safe Binary Document Editing

Date: 2026-08-09

## Status

Accepted

## Context

The owner requires uploaded documents to be viewable and editable in Document workspace. UTF-8
source formats already support this. PDF and DOCX currently expose only read-only extracted content;
plain-text overwrite was deliberately rejected because it would destroy or misrepresent the binary
document.

## Decision

Preserve every PDF/DOCX original as immutable version 1 and expose it separately for inline viewing
where the browser supports it or original download. Treat its bounded canonical extraction as an
explicit editable derivative. Saving creates immutable UTF-8 derivative versions under the existing
optimistic-concurrency, audit, worker, graph and RAG contracts. Never label the derivative bytes as
PDF/DOCX and never overwrite the attachment's original object reference.

## Alternatives Considered

1. Directly write plain text over the original object. Rejected because it corrupts the file-type
   contract and destroys layout fidelity.
2. Integrate a full Office/PDF editing engine. Deferred because it adds a large external rendering,
   conversion and document-part mutation boundary that is not needed for content curation.
3. Continue blocking binary edits. Rejected because it leaves the requested workflow incomplete.

## Consequences

Positive:

- Every readable upload can be corrected and enriched inside Document workspace.
- Original bytes and download provenance remain intact.
- Existing version history, AI review, reprocessing and RAG mechanisms are reused.

Tradeoffs:

- Editing PDF/DOCX changes AI-readable content, not the original page/Office layout.
- Exporting a newly laid-out PDF/DOCX remains a separate future feature.
- Restoring binary version 1 re-extracts it into a new derivative rather than making binary bytes the
  active text editor value.
