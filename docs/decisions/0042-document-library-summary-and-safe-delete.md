# Decision 0042: Document library summary and safe delete

- Status: accepted
- Date: 2026-08-11
- Story: `US-DOCUMENT-LIBRARY-SIMPLIFY-DELETE`

## Context

Uploaded documents need a more useful compact list and a delete action. A workspace also participates
in processing, intake provenance, versioned object storage, RAG, chat, and reviewed graph changes, so
an unbounded cascade could cause invisible data loss.

## Decision

Expose a bounded document summary and reduce the list to Document, Summary, Size, and Actions. Reuse
the existing document workspace as Edit. Allow only owners to delete, require browser confirmation,
and reject deletion while processing is active or when intake/applied-graph provenance retains the
document.

On successful deletion, remove the document-owned workspace data, upload-created research record,
document chat, draft/rejected graph proposals, search projections, and stored source versions while
retaining a content-free audit event.

## Consequences

- Canonical graph knowledge cannot be silently removed from the document library.
- Intake-backed documents require a future explicit retention/receipt workflow before deletion.
- The summary is deterministic and inexpensive; it may be an excerpt until enrichment supplies a
  richer research summary.
- Object deletion follows the validated database delete set; a future trash/retention feature can
  supersede hard delete without changing the list contract.
