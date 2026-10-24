# 0031 Explicit Document-Brainstorm Retry

Date: 2026-08-04

## Status

Accepted and implemented locally; extends the explicit retry rule in decision 0028 to contextual
Document Brainstorm.

## Context

A live DeepSeek Document Brainstorm request reached the accepted 120-second provider deadline and
returned typed HTTP 503. The browser displayed the provider's raw timeout text and offered no way
to retry the question already visible in the chat. Automatically retrying may duplicate a paid
provider call that completed remotely after the local connection ended.

## Decision

Map Document Brainstorm provider, rate-limit, malformed-response and transport failures to
localized stable UI copy. Retain the exact failed question and its pre-request history in ephemeral
browser state. Offer Retry only for retryable failures; Retry is always user-triggered, adds no
duplicate user bubble and uses current source/selection with the saved question/history.

Keep the existing 120-second provider deadline, 125-second frontend proxy budget, stateless API,
redaction/context bounds and explicit Apply boundary unchanged.

## Alternatives Considered

1. Automatically retry once: rejected because it can duplicate cost and work.
2. Increase the provider/proxy deadlines: rejected because it makes an already excessive wait
   longer without addressing provider availability.
3. Fall back silently to another provider: rejected because credentials, model behavior and cost
   differ and provider choice must remain explicit.

## Consequences

- Raw provider diagnostics no longer enter the brainstorm UI.
- A transient failure does not require retyping and Retry does not duplicate the visible question.
- Provider timeouts can still occur; recovery is explicit and cost-aware.
- No document text, source version, chat row, RAG row, graph state or audit body is mutated.
