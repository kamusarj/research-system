# Design

## Domain Model

An unsaved `DocumentAuthorDraft` contains a title, source format, source text,
version and update timestamp. It is browser state, not a canonical Research
System record.

Supported authoring formats are Markdown, UTF-8 text, LaTeX,
reStructuredText, AsciiDoc and HTML. Each maps to the extension and MIME type
already accepted by the document API.

## Application Flow

1. After authentication resolves, load only the cache key scoped to `user.id`.
2. Restore a structurally valid, bounded draft.
3. Persist every title/format/content change locally so refresh cannot discard
   the latest edit.
4. Render source through the existing non-executable source viewer.
5. On Create, generate a sanitized filename and browser `File`.
6. Submit through the existing governed upload helper.
7. If upload succeeds, clear the local cache and navigate to the new workspace.
8. If upload fails, retain the draft and show the typed API error.

## Interface Contract

No backend contract changes. Authored documents use
`POST /api/v1/documents` as multipart files and receive the existing
`DocumentWorkspace` response.

## Data Model

No migration. The browser cache uses one versioned `localStorage` JSON value per
user and origin. It is not canonical storage, is not synced, and is not
included in logs or API calls before explicit creation.

## UI / Platform Impact

`/documents` gains a full-width authoring card above the existing upload and
policy cards. It includes title, source format, content, cache state, discard
and create controls plus the existing side-by-side viewer.

## Observability

Only cache availability/status is rendered. Draft title and body must never
enter console, application, audit or Harness logs.

## Alternatives Considered

1. New JSON authoring API: rejected because the existing upload pipeline already
   owns validation, storage, provenance and processing.
2. Session storage: rejected because closing and reopening the local-first app
   would unnecessarily lose work.
3. One unscoped cache key: rejected because authenticated users sharing a
   browser could see each other's drafts.
4. Server autosave: deferred because it changes canonical retention, schema and
   multi-user concurrency.
