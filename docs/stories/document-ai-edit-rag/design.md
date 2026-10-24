# Design

## Domain Model

`DocumentSourceVersion` is an immutable pointer to one stored source object. The
workspace keeps a monotonically increasing current version. `DocumentAIEditProposal`
binds a replacement to an exact source version, selection range and selected-text
hash. A stale range or version can never be accepted.

Editable formats in this slice are `.md`, `.markdown` and `.txt`. Other accepted
formats retain the existing read-only raw/preview behavior.

## Application Flow

1. Upload creates source version 1 and queues normal document processing.
2. Successful extraction atomically replaces only that research item's vector
   chunks and records document RAG status/count/version.
3. The browser caches the current editor draft per user, workspace and base
   version so F5 restores unsaved work without confusing it with canonical data.
4. Manual Save writes a new immutable object/version, updates current attachment
   pointers, marks RAG pending and requeues processing.
5. AI rewrite validates the current selection, sends only bounded/redacted
   selection context to the configured provider and persists a draft proposal.
6. Accept repeats optimistic checks, creates the next source version and requeues
   processing. Reject only closes the proposal.
7. Restore reads a historical stored object and creates a new current version;
   history is never rewritten.

## Interface Contract

- `GET /api/v1/documents/{id}/versions`
- `POST /api/v1/documents/{id}/versions` for a manual full-source save
- `POST /api/v1/documents/{id}/versions/{version}/restore`
- `POST /api/v1/documents/{id}/ai-edits`
- `POST /api/v1/documents/{id}/ai-edits/{proposal}/accept`
- `POST /api/v1/documents/{id}/ai-edits/{proposal}/reject`
- `POST /api/v1/documents/{id}/rag/rebuild`

All mutation routes require the existing researcher role and CSRF boundary.
Conflict responses are typed and never silently merge divergent source.

## Data Model

- Add `document_source_versions` with unique `(workspace_id, version_number)` and
  immutable object/hash/size/origin/actor metadata.
- Add `document_ai_edit_proposals` with base version, selection/hash, bounded
  replacement, provider/model provenance and lifecycle status.
- Add current source-version and RAG status/count/version/error/timestamp fields
  to `document_graph_workspaces`.
- Reuse `search_vector_projections`; draft document rows are retained during the
  approved-only global rebuild and semantic global reads explicitly filter to
  approved research.

The migration backfills version 1 from existing attachment/workspace pointers;
it copies no bytes and deletes no document objects.

## UI / Platform Impact

The existing document source panel becomes an editor only for Markdown/TXT and
authorized researchers. A selection toolbar exposes Improve, Shorten, Expand,
Fix grammar and custom instruction actions. A comparison card shows selected and
proposed text with Accept/Reject. Version history supports restore. Raw/Preview/
Side-by-side remains responsive and non-executable.

## Observability

Audit events record workspace/version/proposal IDs, hashes, action, provider and
aggregate sizes only. Document content, selection, replacement and provider raw
responses never enter logs or audit payloads. RAG failure is visible through a
typed status/error code without failing extraction or graph review.

## Alternatives Considered

1. Store version bodies directly in PostgreSQL. Rejected because object storage
   already owns document durability and version objects preserve the same local/
   MinIO routing boundary.
2. Add a second document-RAG table. Rejected because the current pgvector model,
   chunking and retrieval already satisfy the contract.
3. Apply AI responses immediately. Rejected because it violates the project's
   human-review and no-silent-overwrite rules.

