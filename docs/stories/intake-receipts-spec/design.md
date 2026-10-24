# Design

## Domain Model

`IntakeReceipt` is a durable external occurrence. `IntakeReceiptItem` is one URL or document within
that occurrence. `LinkSubmission` and `DocumentGraphWorkspace` remain processing aggregates.
Repeated occurrences link new items to existing aggregates; identical delivery replays converge.

## Application Flow

1. Authenticate the user/service account and validate a bounded source descriptor.
2. Normalize source identity and compute a server-side receipt hash.
3. Load/create the receipt under a database uniqueness constraint.
4. Normalize/fingerprint each URL or validate, hash, and store each document.
5. Load/create the appropriate processing aggregate and insert the receipt item atomically.
6. Persist initial `queued`/`linked_existing`; return `replayed` only as the current delivery result.
7. Project linked processing/review states for polling; never publish from receipt state.

## Interface Contract

- `POST /api/v1/intake/receipts` accepts one source occurrence and bounded URL items.
- `POST /api/v1/intake/receipts/{id}/documents` persists a document item before acknowledgement.
- `GET /api/v1/intake/receipts/{id}` returns bounded aggregate/item status.
- `/api/v1/ingestion/links` remains a compatibility endpoint that creates an implicit receipt.
- Typed conflicts distinguish occurrence identity collision from attachment ref/content mismatch.

## Data Model

- `intake_receipts`: source type/namespace/occurrence, unique delivery hash, safe source context,
  authenticated actor, delivery count, first/last seen timestamps.
- `intake_receipt_items`: receipt/ordinal/kind/fingerprint, safe URL or content digest, one processing
  foreign key, immutable initial disposition, timestamp, plus document-ref conflict uniqueness.
- Additive backfill preserves all processing state and creates exactly one linked item for every
  legacy submission. Legacy provenance columns remain during rollback/verification.

## UI / Platform Impact

Manual UI behavior remains compatible but may display occurrence and item disposition. External
adapters obtain receipt IDs and poll status. The future Discord adapter maps one message to one
receipt and multiple URLs/PDFs to items; it owns no research business logic.

## Observability

Audit stores safe IDs, source type, disposition, item kind and counts with hashed external refs.
Logs/metrics use bounded actions and outcomes only. No platform payload, raw URL, filename, message
body, username, token, or document content is logged.

## Alternatives Considered

1. Keep one `LinkSubmission` per URL and overwrite `source_ref`: rejected because later provenance
   is lost.
2. Create one `LinkSubmission` per occurrence: rejected because retries and repeated URLs duplicate
   fetch/AI work and weaken canonical processing state.
3. Store an untyped JSON list of occurrences on `LinkSubmission`: rejected because concurrency,
   indexing, referential integrity, multi-item messages, and retention cannot be enforced safely.
4. Put occurrence state in the Discord bot: rejected because the adapter would become a second
   source of truth and other intake channels could not share the contract.
