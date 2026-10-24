# Intake Occurrence and Receipt Specification

Status: implemented and locally verified; Discord adapter has not started.

Date: 2026-07-21

## 1. Purpose

The Research System must preserve every meaningful source occurrence without creating duplicate
fetch/classification jobs for the same canonical URL. This contract is source-neutral: manual UI,
API clients, future Discord, and later adapters all submit occurrences and items through the same
boundary. A platform adapter never owns extraction, deduplication, review, publication, search, or
graph logic.

This design is a prerequisite for Discord Gate D. It does not authorize the Discord bot, production
credentials, a database migration, or external deployment while Graph v2 acceptance and
deployment-owned Gate C operations remain open.

## 2. Implemented Behavior

`link_submissions.url` remains the unique URL processing aggregate, while additive
`intake_receipts` and `intake_receipt_items` tables now preserve each source occurrence. The
source-neutral endpoints support multiple URLs and durable document items; the legacy
`POST /api/v1/ingestion/links` endpoint dual-writes an implicit receipt without changing its
existing top-level response fields.

Migration `a8b4c6d2e913` backfilled every existing link without fetching, reprocessing, or changing
processing/review/research state. The implementation was verified with concurrent API tests, a
PostgreSQL backup/restore and live backfill check, and read-back against a disposable real MinIO
server. Revocable service accounts store only token hashes and are restricted to their own source
namespace and the `intake:submit` / `intake:read-own` scopes.

## 3. Terminology and Invariants

- **Receipt**: one durable external occurrence or delivery, such as a manual submit action, API
  request, or Discord message. It owns source provenance, not extraction state.
- **Receipt item**: one URL or uploaded document observed in a receipt.
- **Processing aggregate**: the canonical job that performs URL or document processing. Existing
  `LinkSubmission` and `DocumentGraphWorkspace` remain the processing aggregates.
- **Replay**: another delivery with the same stable occurrence identity and item fingerprint.
- **Repeated occurrence**: the same URL or bytes observed through a different source occurrence.

The following invariants are mandatory:

1. A new occurrence is recorded even when its URL or content already has a processing aggregate.
2. Replaying the same occurrence and item creates no second receipt, item, job, or object.
3. One receipt may contain multiple URL and document items.
4. A receipt item links to exactly one processing aggregate after acceptance.
5. URL normalization happens before item fingerprinting or lookup.
6. Document bytes are validated and durably stored before an asynchronous job is acknowledged.
7. Receipt delivery is append-only: a later delivery may add items but never erases earlier
   provenance.
8. PostgreSQL remains canonical; queues, Discord, search, and graph are not sources of truth.
9. The API never stores message bodies, usernames, display names, secrets, tokens, or arbitrary
   platform payloads in receipt metadata or audit events.
10. No receipt state can approve or publish research; existing human review and RBAC still apply.

## 4. Domain Model

### 4.1. `IntakeReceipt`

An `IntakeReceipt` records one source occurrence.

| Field | Contract |
| --- | --- |
| `id` | Server UUID. |
| `source_type` | Allowlisted adapter type such as `manual`, `api`, or `discord`. |
| `source_namespace` | Stable non-secret connector/installation namespace; `local` for manual UI. |
| `external_occurrence_ref` | Bounded opaque event reference. Discord uses its message ID. |
| `delivery_key_hash` | SHA-256 receipt key; unique and never returned. |
| `container_ref` | Optional bounded opaque channel/thread/container reference. |
| `submitted_by` | Authenticated local user or service-account actor ID. |
| `external_actor_ref_hash` | Optional SHA-256 only; never a username or display name. |
| `metadata` | Versioned, allowlisted scalar metadata only. |
| `delivery_count` | Number of accepted deliveries/replays for diagnostics. |
| `received_at` / `last_seen_at` | First and latest accepted delivery timestamps. |

For a client-supplied occurrence identity, the server computes:

```text
SHA256(
  "receipt-v1" + NUL + source_type + NUL + source_namespace + NUL + external_occurrence_ref
)
```

External adapters must supply all three identity fields. Manual callers may provide an idempotency
key; otherwise the server creates a new occurrence UUID for each explicit submit action. The key is
never derived from message content.

### 4.2. `IntakeReceiptItem`

An `IntakeReceiptItem` records one observed URL or document.

| Field | Contract |
| --- | --- |
| `id` | Server UUID. |
| `receipt_id` | Required foreign key to `intake_receipts`. |
| `ordinal` | Stable first-seen order within the receipt. |
| `kind` | `url` or `document`. |
| `item_key_hash` | SHA-256 fingerprint, unique within a receipt. |
| `normalized_url` | URL snapshot for URL items; null for documents. |
| `external_item_ref` | Optional bounded adapter item/attachment reference. |
| `content_sha256` | Required for document items after byte validation. |
| `link_submission_id` | Nullable foreign key for URL processing. |
| `document_workspace_id` | Nullable foreign key for document processing. |
| `initial_disposition` | Immutable creation result: `queued` or `linked_existing`. |
| `created_at` | First accepted timestamp. |

A check constraint requires exactly one processing reference after the item is accepted. The item
fingerprints are:

```text
URL:      SHA256("url-v1" + NUL + normalized_url)
Document: SHA256("document-v1" + NUL + external_item_ref + NUL + content_sha256)
```

The unique constraints are `intake_receipts.delivery_key_hash`,
`(intake_receipt_items.receipt_id, intake_receipt_items.item_key_hash)`, and a partial unique
document constraint on `(receipt_id, kind, external_item_ref)` when the external ref is present. A
second message containing the same URL therefore creates another item linked to the existing
`LinkSubmission`; the same message and normalized URL reuses the original item. Reusing one
document ref with different bytes hits the document constraint and returns `SOURCE_ITEM_CONFLICT`.

### 4.3. Aggregate Status

Receipt status is derived from its linked processing aggregates and is not another workflow state
machine. Each item exposes its current target status and review status. The receipt summary is one
of `queued`, `processing`, `needs_review`, `approved`, `partial_success`, `failed`, or `mixed`.
`mixed` is used when terminal item outcomes differ.

Content-level duplicates discovered after fetch remain explicit `LinkSubmission` outcomes. Receipt
items are never reparented or deleted; they continue to point to the processing history that
observed the duplicate and resolve its linked research ID when available.

## 5. Source-Neutral API Contract

### 5.1. Create or replay a receipt

```http
POST /api/v1/intake/receipts
```

```json
{
  "source": {
    "type": "discord",
    "namespace": "research-connector",
    "occurrence_ref": "opaque-event-id",
    "container_ref": "opaque-container-id"
  },
  "items": [
    {
      "kind": "url",
      "url": "https://example.com/research",
      "provider": "mistral"
    }
  ]
}
```

The source object and item list are bounded. Unknown metadata keys fail validation; the server does
not accept an arbitrary platform payload. The response contains the receipt ID, `replayed`, current
aggregate status, and each item ID, delivery disposition, processing reference, and safe status
projection. `replayed` is computed for that delivery and never overwrites the item's immutable
`initial_disposition`.

- Return `202` when at least one new processing job is queued.
- Return `200` when all items replay or link to existing processing aggregates.
- Return `409 SOURCE_OCCURRENCE_CONFLICT` when an existing occurrence identity is reused with
  incompatible source identity.
- Return `409 SOURCE_ITEM_CONFLICT` when one external attachment reference is reused with different
  bytes.
- Return typed `422` errors for invalid/oversized item sets, URLs, metadata, or content types.

Delivering an edited source event is a merge: known items replay and new items append. Items omitted
from a later delivery remain as provenance and do not trigger deletion or cancellation.

### 5.2. Upload a document item

```http
POST /api/v1/intake/receipts/{receipt_id}/documents
Content-Type: multipart/form-data
```

The request includes the bounded external item reference plus one currently supported document
type. Initial Discord scope is public PDF attachments; the source-neutral boundary may reuse the
existing PDF/Markdown/text validation rules.

The API must validate filename, MIME type, file signature, size, and SHA-256; persist the bytes via
the routed object-storage boundary; create the draft research/document workspace and receipt item;
then return `202`. A database failure after object write triggers best-effort object cleanup and a
reconciliation signal. The API never returns success before durable object storage and database
commit both succeed.

### 5.3. Read receipt status

```http
GET /api/v1/intake/receipts/{receipt_id}
```

The response contains bounded item status projections and may use ETag/conditional polling. Initial
Discord behavior polls with backoff and maps states to reactions/replies; no webhook or platform
callback is required in the first adapter.

Existing `POST /api/v1/ingestion/links` remains a compatibility endpoint during migration. It
creates an implicit single-item receipt and preserves its current top-level submission fields while
adding receipt identifiers/disposition. It must no longer discard a later source occurrence merely
because the URL already exists.

## 6. Authorization, Privacy, and Audit

- Browser users require the existing `researcher` role to submit and the existing owner permissions
  to approve/publish.
- External adapters require a revocable service account with narrow `intake:submit` and
  `intake:read-own` capabilities before Gate D. A Discord bot token is never accepted by the
  Research API and never stored in PostgreSQL.
- A service account may read only receipts in its own `source_namespace`; owner operators may read
  all receipts.
- Audit records include action, receipt/item ID, source type, disposition, item kind, counts, and
  hashed external references. They exclude URLs with query strings, message text, filenames,
  usernames, platform tokens, transcript bodies, and document bytes.
- Application logs and metrics use bounded actions/outcomes only. Raw source refs, normalized URLs,
  attachment names, and actor references are not log or metric labels.
- Receipt metadata is allowlisted and versioned. Discord may retain opaque guild/channel/message
  technical refs needed for provenance, but never message content or member profile fields.

## 7. Concurrency and Transaction Rules

Receipt and URL-item creation run in one database transaction with uniqueness constraints as the
final concurrency guard. Two simultaneous identical deliveries converge to one receipt, one item,
and at most one processing job; the losing transaction reloads and returns the committed result.

Creating a new occurrence for an existing normalized URL locks or upserts the canonical
`LinkSubmission`, then inserts a new receipt item pointing to it. Provider and `auto_approve`
settings from a repeated occurrence do not mutate an already active/completed processing job.
Changing those settings remains an explicit retry/reprocess operation with existing authorization.

Document bytes cross an object-store/database boundary. The service uses create-if-absent object
names derived from a server UUID, verifies the content digest after write, and commits the workspace
and receipt item afterward. Orphan reconciliation is operational cleanup, never a reason to point a
receipt at unverified bytes.

## 8. Additive Migration and Rollout

1. Add `intake_receipts` and `intake_receipt_items`; retain existing `link_submissions` columns and
   its normalized-URL uniqueness.
2. Backfill existing submissions without fetching or reprocessing:
   - group non-null legacy rows by `(source_type, source_ref)` into one legacy receipt;
   - create one receipt per submission when `source_ref` is null;
   - add one URL item for every existing submission and link it directly;
   - mark only safe metadata with `schema_version=1` and `legacy_backfill=true`.
3. Verify every `LinkSubmission` has exactly one backfilled item, all item references resolve, no
   processing/review/research state changed, and counts are stable.
4. Enable dual-write through the compatibility endpoint, then switch reads to receipt projections.
5. Keep legacy `source_type`, `source_ref`, and `submitted_by` columns for rollback. Removing them is
   a separate, explicitly approved migration after production evidence.

Runtime rollback uses the prior application while leaving additive tables intact. Once new receipt
data exists, an automated schema downgrade that drops those tables is data loss and is not a
production rollback mechanism. Production rollout requires a PostgreSQL backup and restore proof.

## 9. Validation Contract

The implementation proof covers:

- unit tests for key derivation, URL normalization order, bounded metadata, aggregate status, and
  attachment fingerprints;
- integration tests proving same occurrence + same URL is a replay, different occurrence + same URL
  creates distinct provenance but one URL job, and one occurrence accepts multiple URLs;
- a concurrent duplicate-delivery test proving one receipt/item/job;
- document tests proving bytes exist and hashes match before `202`, replay is a no-op, conflicting
  bytes fail, and failed database commit does not leave a referenced missing object;
- migration upgrade/model parity/downgrade/upgrade on disposable data plus PostgreSQL backfill count
  and referential-integrity proof;
- compatibility tests for the current manual intake UI and `/ingestion/links` clients;
- authorization tests for service namespace isolation and owner visibility;
- log/audit scans proving raw platform references, URLs, filenames, message content, and secrets are
  absent;
- desktop/tablet/mobile E2E for manual intake and an adapter-contract integration test using a fake
  source-neutral client, not a live Discord bot.

## 10. Gate D Entry Criteria

Discord implementation may start only when all of the following are true:

1. Graph Intelligence v2 product-owner acceptance is recorded.
2. Required deployment-owned Gate C controls are accepted for the target environment.
3. This receipt model is implemented, migrated, and verified against PostgreSQL and routed object
   storage. **Satisfied for the local runtime; target-environment rollout remains operational
   work.**
4. Revocable scoped service-account authentication exists. **Satisfied.**
5. Guild/channel allowlist, permitted attachment/media policy, token deployment, rate limits, and
   status-reply behavior have explicit operational owners.

The first Discord adapter then only parses one message into receipt items, uploads permitted PDF
bytes, submits through this contract, polls receipt status, and reports outcomes. It contains no
fetch, AI, deduplication, publication, search, or graph business logic.
