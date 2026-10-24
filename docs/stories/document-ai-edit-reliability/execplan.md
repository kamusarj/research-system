# Exec Plan

## Goal

Eliminate proxy-induced instant-edit 500s and simplify Document workspace without removing required
editing, preview, AI, cache, upload or document-list behavior.

## Scope

In scope:

- Aligned proxy/API timeout budgets.
- Typed malformed-provider handling.
- Localized, retryable editor errors.
- Collapsed preview and reduced duplicated UI.
- Focused unit/component/E2E/runtime proof.

Out of scope:

- Provider streaming or job queues.
- Automatic retries.
- Database/migration/RAG changes.
- Rich PDF/DOCX editing.

## Risk Classification

Risk flags:

- External systems.
- Public contracts.
- Cross-platform.
- Existing behavior.
- Audit/security.

Hard gates:

- External provider behavior.

## Work Phases

1. Correlate proxy and API timing logs.
2. Align timeouts and type provider parse failures.
3. Add localized retry behavior.
4. Simplify authoring hierarchy and preview disclosure.
5. Run focused/full tests, build and responsive runtime proof.
6. Update Harness and AI handoff logs.

## Stop Conditions

Pause if the fix would require provider credential changes, automatic paid retries, weaker
redaction, persistence changes or removal of requested preview modes.
