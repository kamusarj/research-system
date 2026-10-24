# Design

## Domain Model

`KnowledgeGap` remains the persisted gap lifecycle aggregate. Gap detection stays in the
API and derives low-coverage gaps from tags on approved `ResearchItem` rows. A receipt
item exposes a bounded `KnowledgeGapSummary` only when its linked approved research item
has the same normalized concept key and the gap remains active.

No Discord-specific gap state and no new database relation are introduced.

## Application Flow

```text
allowlisted Discord URL
  -> receipt item with auto_approve=true
  -> existing bounded fetch/extract/classify worker
  -> complete + confidence threshold
  -> existing research approval and ontology change-set proposal
  -> refresh persisted low-coverage gaps
  -> scoped receipt poll reads related active gaps
  -> bilingual Discord channel reply
```

Low-confidence and partial sources stop at the existing review state. A public Reel
without a supplied transcript therefore remains partial and receives the existing
actionable message rather than being published from metadata alone.

## Interface Contract

Each `ReceiptItemRead` gains `knowledge_gaps`, defaulting to an empty list. Each summary
contains only `id`, `title`, `concept_key`, `status`, `priority`, `coverage_count`, and
`reason`. The service-account authorization boundary is unchanged because the information
is projected through the already namespace-confined receipt read.

The gateway gains `DISCORD_AUTO_APPROVE_LINKS`, default `true`. It controls only whether
the receipt asks the API to use its existing guarded auto-approval path.

## Data Model

No migration. Existing `knowledge_gaps`, `research_items`, tags, receipt items, and link
submissions remain authoritative.

## UI / Platform Impact

Discord replies add a clearly labeled, bounded knowledge-gap section in English or
Vietnamese. The Compose `discord` profile forwards the new non-secret configuration.

## Observability

The existing approval and receipt logs remain content-safe. Gap detection continues to
write persisted state; Discord logs do not include message bodies, URLs, gap reasons, or
credentials.

## Alternatives Considered

1. Let the bot call `/gaps/detect`: rejected because it would require a new mutation scope
   and move orchestration authority into an external adapter.
2. Give the bot owner credentials: rejected because it breaks the accepted least-privilege
   boundary.
3. Automatically approve/apply ontology change sets: rejected because the request can be
   met through the approved research relationship graph while preserving canonical
   hierarchy governance.
4. Store Discord-specific gap notifications in new tables: rejected because related gaps
   can be projected deterministically from canonical research tags.
