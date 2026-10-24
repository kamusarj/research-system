# Design

## Domain Model

`DocumentAuthorDraft` remains versioned browser state containing title, editable
source format, content and update time. It is bounded to two million characters,
scoped to the authenticated user and browser origin, and is not canonical data.

## Application Flow

1. Restore a valid draft for the current user when Document Workspace mounts.
2. On every title, format, import or content change, synchronously write the
   complete next draft to `localStorage` before the event handler returns.
3. Preserve the draft across refresh, navigation, tab close and browser restart.
4. Retain the cache after upload or provider errors.
5. Clear the cache only after `POST /api/v1/documents` succeeds, then navigate to
   the created workspace.

## Interface Contract

The `Discard local draft` / `Xoá bản nháp cục bộ` control is removed from the
authoring footer and its translation catalog entry is retired. The existing
saved/restored/cache-unavailable status remains visible. No API contract changes.

## Data Model

No migration. The existing versioned `localStorage` key and value shape remain
unchanged, so existing browser drafts continue to restore after rollout.

## UI / Platform Impact

The authoring footer contains only the governed Create action. Desktop, tablet
and mobile share the same behavior. Synchronous Web Storage writes provide the
crash/restart recovery boundary already used by this feature.

## Observability

No document title or body enters logs, audit records or Harness evidence. Tests
assert visible cache state and storage behavior without recording real content.

## Alternatives Considered

1. Add server autosave. Rejected for this request because it would introduce
   retention, authorization, concurrency, schema and network-failure semantics.
2. Keep Discard behind confirmation. Rejected because the owner requested the
   destructive draft action be removed, not made harder to click.
3. Debounce browser writes. Rejected because a delay creates an avoidable loss
   window immediately before a crash or accidental close.

