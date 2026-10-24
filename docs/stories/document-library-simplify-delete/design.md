# Design

## Domain Model

An uploaded document owns a workspace, an upload-created research item, its attachment, source
versions, extracted graph/evaluation records, RAG projections, and document-scoped chat. Its list
summary is a bounded normalized projection of `ResearchItem.summary`, falling back to extracted
content.

Deletion is permitted only when processing is inactive, no intake receipt retains the workspace, and
no document-origin graph change set has reached `applied`.

## Application Flow

`GET /documents` serializes a bounded summary. The list opens the existing editor for Edit. An owner
confirms Delete, calls the API, and refetches the query after success.

`DELETE /documents/{document_id}` validates the guards, removes document-owned database records and
the upload-created research record, records an audit event, commits, and removes the distinct stored
objects.

## Interface Contract

- `DocumentWorkspaceRead.summary: string` is always present and bounded to 500 characters.
- `DELETE /api/v1/documents/{document_id}` returns `204`.
- `409 DOCUMENT_DELETE_IN_PROGRESS` protects active jobs.
- `409 DOCUMENT_DELETE_PROVENANCE_LOCKED` protects intake and applied-graph provenance.
- Existing global route policy makes DELETE owner-only.

## Data Model

No schema migration is required. Existing ownership keys and relationships define the delete set.
Audit events are retained; pending outbox work for the deleted workspace is removed.

## UI / Platform Impact

Desktop and mobile tables use four columns: Document, Summary, Size, Actions. Delete is hidden for
non-owners and disabled while its request is in flight.

## Observability

`document.deleted` records workspace, research, filename, content hash, and object count without
storing document content or object keys.

## Alternatives Considered

1. Soft-delete was rejected because the requested library behavior is removal and there is no current
   archived-document product surface.
2. Cascading applied graph data was rejected because it would silently destroy reviewed canonical
   knowledge and provenance.
