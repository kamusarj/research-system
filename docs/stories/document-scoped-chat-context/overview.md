# Document-scoped chat context

## Current Behavior

Document-scoped chat receives paper-fit metadata and bounded document graph nodes. It can retrieve
node evidence through a guarded tool, but it does not receive canonical extracted document text,
so questions about passages not selected into the graph may lack source context.

## Target Behavior

Document-scoped chat receives a bounded canonical text excerpt from the linked ResearchItem in its
authorized scope context. The existing redaction function runs before provider transmission, the
overall context limit still applies, and document text remains untrusted data.

Status: implemented and verified on 2026-07-30.

## Affected Users

- Local owner and researcher using document-scoped brainstorm chat.

## Affected Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `AI_LOGS/DECISIONS.md` (DEC-019 remains the governing decision)

## Non-Goals

- Sending original binary bytes or raw source markup to chat providers.
- Increasing the configured overall chat-context limit.
- Changing provider retention, publication permissions or graph governance.
