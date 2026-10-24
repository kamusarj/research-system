# 0017 Discord Ingest and Knowledge-Gap Alerts

Date: 2026-07-30

## Status

Accepted

## Context

The existing Discord gateway submits source-neutral receipts with a least-privilege
service account and polls their state. URL items do not currently request the system's
guarded auto-approval path, gap detection remains an explicit workspace action, and
receipt status cannot tell the gateway whether an approved item exposes a relevant
knowledge gap.

The requested workflow is zero-touch for eligible links: submit, process into the graph,
and notify the channel when the resulting approved knowledge remains under-covered.

## Decision

Discord URL receipt items request `auto_approve=true` by default, controlled by a
deployment setting. The API keeps the existing complete-source and confidence guards;
partial or low-confidence sources still require review.

After a link is approved, the API refreshes the persisted low-coverage gap projection.
Namespace-scoped receipt reads include bounded summaries of active gaps whose concept key
matches a tag on that receipt item's approved research record. The Discord gateway renders
those summaries in its normal bilingual channel reply.

The bot retains only `intake:submit` and `intake:read-own`. Canonical hierarchy mutations
remain governed change-set proposals requiring human review and application.

## Alternatives Considered

1. Give the bot direct gap-detection or owner scopes. Rejected because an external adapter
   must not gain research or graph mutation authority.
2. Apply ontology change sets automatically. Rejected because this weakens existing graph
   governance and is unnecessary for the approved research relationship graph.
3. Detect gaps in the bot. Rejected because PostgreSQL and the API own research state and
   gap lifecycle rules.
4. Auto-publish partial Reels from public metadata. Rejected because it would weaken the
   accepted transcript/evidence boundary.

## Consequences

Positive:

- Eligible Discord links complete the existing guarded intake-to-approved-graph path.
- Channel users see relevant knowledge gaps without opening the web workspace.
- The bot remains stateless, replaceable, and least-privileged.

Tradeoffs:

- Low-confidence sources and Reels without transcripts still stop for human action.
- Gap alerts are a current projection on receipt reads, not a durable Discord delivery
  ledger.
- Canonical hierarchy placements still require the existing owner review workflow.

## Follow-Up

- Run the gateway against an owner-provided Discord application/token and allowlist.
- Add a durable callback/outbox delivery story only if operators require alerts after a
  receipt's finite polling window has ended.
