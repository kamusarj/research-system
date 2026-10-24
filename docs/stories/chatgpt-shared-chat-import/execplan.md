# Exec Plan

## Goal

Let a researcher fork a public ChatGPT shared conversation into the local governed chat workspace
and continue it without any ChatGPT write-back.

## Scope

In scope:

- Strict official-share URL validation and bounded cookie-free retrieval.
- Public snapshot parsing for current React loader and legacy share payloads.
- Additive local provenance/message-origin persistence and migration parity.
- One import API plus bilingual responsive browser workflow.
- Existing provider-neutral local continuation, redaction and graph governance.

Out of scope:

- Private/authenticated ChatGPT chats, downloadable attachments, non-public image pointers, hidden
  reasoning and raw tool output. Public generated-image tool media is retained without tool text.
- Live synchronization, shared-link refresh in place, bulk imports or ChatGPT mutation.
- A new AI provider or changes to graph proposal/apply authority.

## Risk Classification

Risk flags:

- Data model.
- Audit/security.
- External systems.
- Public contracts.
- Existing behavior.

Hard gates:

- External public-content retrieval and security boundary.
- Additive migration and durable transcript retention.

## Work Phases

1. Record intake #33, this story and DEC-035/decision 0022.
2. Add deterministic parser and strict bounded fetch service.
3. Add migration, schemas, service transaction and API route.
4. Add bilingual import UI, provenance labels, sanitized GFM rendering, bounded anonymous image
   resolution/local caching and same-origin image presentation.
5. Add parser/fetch/API/migration/frontend/E2E-focused tests.
6. Run focused and full verification, update runtime/docs/Harness/AI logs.

## Stop Conditions

Pause for human confirmation if:

- Import requires ChatGPT credentials, login cookies or a private endpoint.
- The exact-host/SSRF or size limits would need weakening.
- Source transcript deletion or write-back becomes necessary.
- Existing chat publication or provider-retention rules must change.
