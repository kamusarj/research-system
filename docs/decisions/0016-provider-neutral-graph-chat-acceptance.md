# 0016 Provider-Neutral Graph Chat Acceptance

Date: 2026-07-21

## Status

Accepted

## Context

Graph Intelligence v2 chat orchestration and governance were designed behind a provider protocol,
but the only implemented tool-calling adapter and the final acceptance gate required OpenAI. The
current OpenAI credential is rejected, while DeepSeek is already configured and has successfully
processed real project documents. The product owner explicitly authorized DeepSeek as a temporary
graph-chat provider and asked to switch back to OpenAI later.

## Decision

Support both DeepSeek Chat Completions tool calling and OpenAI Responses behind the existing graph
chat provider boundary. Use `GRAPH_CHAT_DEFAULT_PROVIDER=deepseek` for the current acceptance run;
allow a later environment-only switch to `openai`. DeepSeek runs in non-thinking mode, receives only
bounded redacted context and read/propose tools, and returns tool arguments to the same Pydantic
validation and draft change-set workflow. Provider choice never grants publish/delete authority.

## Alternatives Considered

1. Wait indefinitely for a replacement OpenAI credential. Rejected by the product owner because it
   blocks completion despite an available provider-neutral design and configured DeepSeek access.
2. Reuse the document-classification adapter without native graph tools. Rejected because it would
   bypass the governed multi-step read/propose orchestration.
3. Enable DeepSeek strict-tool beta. Deferred because the current schemas include constraints not
   supported by the beta subset; application-side Pydantic validation remains mandatory.

## Consequences

Positive:

- The real acceptance walkthrough can proceed without weakening graph governance.
- Existing OpenAI sessions and the OpenAI `store=false` adapter remain available.
- Switching the default provider later requires configuration and service recreation, not schema or
  frontend changes.

Tradeoffs:

- Provider request envelopes differ and require adapter-specific unit and real-provider proof.
- DeepSeek does not receive local metadata identifiers; request provenance remains whatever safe ID
  the provider returns plus local provider/model/prompt-version records.

## Follow-Up

- Complete a real DeepSeek scoped brainstorm and grounded proposal walkthrough.
- Switch `GRAPH_CHAT_DEFAULT_PROVIDER` back to `openai` only after its credential preflight passes.
