# Design

## Domain Model

- `IntakeReceipt`: source occurrence identity, server hash, namespace, safe context, authenticated
  actor and replay counters.
- `IntakeReceiptItem`: ordered URL/document occurrence item with a server fingerprint and exactly one
  linked `LinkSubmission` or `DocumentGraphWorkspace`.
- `ServiceAccount`: revocable bearer credential stored only as SHA-256, fixed intake scopes and one
  source namespace. Raw token is returned only on creation.

## Application Flow

1. Middleware resolves a cookie session, trusted-local owner, or bearer service account.
2. Service principals are limited to receipt submit/document/read routes and their own namespace;
   bearer mutations do not use browser CSRF.
3. Receipt delivery normalizes URLs, computes hashes and transactionally creates/reloads receipt,
   canonical jobs and ordered items under uniqueness constraints.
4. Replays increment safe delivery counters and return existing items. Different occurrences link
   new items to the existing URL job without mutating provider/review state.
5. Document delivery stores and hashes bytes first. Same item/hash replays, same ref/different hash
   conflicts, and same bytes in another occurrence link the existing workspace. New document
   workspace plus receipt item commit together; failure deletes the newly written object.
6. Compatibility `/ingestion/links` creates an implicit single-item receipt while retaining current
   top-level response and status-code semantics.

## Interface Contract

- `POST /api/v1/intake/receipts`
- `POST /api/v1/intake/receipts/{id}/documents`
- `GET /api/v1/intake/receipts/{id}`
- Owner-only list/create/revoke under `/api/v1/auth/service-accounts`.
- Typed receipt conflicts use `SOURCE_OCCURRENCE_CONFLICT` and `SOURCE_ITEM_CONFLICT`.

## Data Model

Migration after `c5a8e2f4b901` adds the three tables and indexes/check constraints. It backfills one
URL item for every legacy submission, grouping rows with the same non-null `(source_type,
source_ref)` into one legacy receipt and creating one receipt per null source ref. Existing job,
review, research and object state is not changed. Downgrade is allowed only when no non-backfill
receipt/service-account data exists; otherwise it fails rather than erase new provenance.

## UI / Platform Impact

The manual UI remains compatible and gains additive receipt identifiers in API results. No Discord
or new browser screen is required. Owner service-account operations are API/operator surfaces.

## Observability

Business audit includes IDs, source type, item kind, disposition/count and hashed external refs; it
never includes raw tokens, raw URLs, filenames, message content or platform profiles. Application
logs use existing allowlisted request/job fields.

## Alternatives Considered

1. Implement receipts without service accounts: rejected because Gate D would expose a broad browser
   credential or require a second auth design.
2. Reuse user passwords/sessions for adapters: rejected because cookies/CSRF and human identity do
   not provide namespace-scoped revocation.
3. Make document upload two non-transactional API calls: rejected because a receipt could point to
   missing bytes or an unowned workspace.

