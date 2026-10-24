# 0024 Human-Reviewed Document AI Editing and Automatic RAG

Date: 2026-08-02

## Status

Accepted

## Context

Editable sources are currently read-only after upload and their unsaved cache
exists only before creation. Document-scoped chat can use pgvector passages, but
uploaded drafts are not projected until an owner rebuilds the approved-only
search projection. The owner requires inline AI editing, durable undo/history,
refresh recovery and automatic RAG as one document workflow.

## Decision

Support in-place Markdown/TXT editing through immutable object-backed source
versions and optimistic concurrency. AI operates only on an explicitly selected,
bounded range and creates a persisted draft replacement. Only a researcher or
owner's explicit Accept creates a new source version; reject is non-mutating.

After every successful extraction, replace that document's chunks in the existing
Mistral `mistral-embed` / pgvector projection and record RAG state on the document
workspace. Draft document chunks are scoped retrieval data, never canonical
research and never global approved search results. Approved projection rebuilds
preserve current draft-document chunks.

Editor cache remains versioned localStorage scoped to authenticated user,
workspace and base source version. Server versions, not browser cache, are the
durable recovery source.

## Alternatives Considered

1. Auto-apply AI rewrites. Rejected because uploaded text may be sensitive or
   authoritative and the system forbids silent AI overwrite.
2. Store version bodies only in PostgreSQL. Rejected in favor of the existing
   routed object-storage durability and migration boundary.
3. Add LightRAG or a second vector store. Rejected because DEC-034 and DEC-021
   already establish the custom pgvector retrieval path.
4. Rich-edit DOCX/PDF in this slice. Deferred because byte-faithful round trips,
   pagination/layout and document-part mutation require separate format designs.

## Consequences

Positive:

- Every accepted change is attributable, reversible and conflict-safe.
- Document chat can retrieve fresh passages immediately after processing draft
  uploads/edits without exposing those drafts in global search.
- The editor gives immediate AI assistance while preserving human authority.

Tradeoffs:

- Historical object versions increase storage use and require future retention
  policy; this slice deliberately does not delete them.
- Embedding refresh adds bounded provider cost after each processed version and
  can fail independently with a visible retry state.
- Browser cache remains local, unencrypted and non-collaborative.

## Follow-Up

- Design DOCX/PDF rich editing and version retention as separate high-risk work.
- Consider collaborative server drafts only with an explicit lock/merge model.
