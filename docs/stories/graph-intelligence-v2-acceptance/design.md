# Design

## Domain Model

This story uses the existing document workspace, isolated graph, graph change set, canonical graph,
chat session/message and provider-provenance models. It introduces no schema or domain changes.

## Application Flow

1. Start only `database`, `api`, `worker`, and `frontend` with documented port overrides.
2. Require health, feature and graph-readiness checks.
3. Confirm only whether the selected server-side graph-chat credential is configured, then execute
   a bounded secret-safe operator preflight and provider-backed chat turn through the application
   contract.
4. Upload a deterministic text document, wait for processing, inspect evaluation/graph evidence,
   create a mapping change set, reject one mutation, approve/apply the rest, and inspect history.
5. Exercise scoped chat draft behavior when provider access succeeds.
6. Run responsive and typed-error checks, record evidence, and leave the final decision to Linh.

## Interface Contract

Use the existing `/api/v1/system`, `/api/v1/documents`, `/api/v1/ontology`,
`/api/v1/graph/change-sets`, and `/api/v1/chat` contracts without changing response shapes.
`python -m app.operations verify-chat-provider` is the operator-only preflight for the configured
default; `--provider openai|deepseek` selects explicitly. It performs one minimal request and emits
only allowlisted readiness fields, never provider content or IDs. Provider-specific API-only secret
overlays support replacement without requiring every credential in the managed-deployment overlay.

## Data Model

No migrations. Acceptance records are ordinary local PostgreSQL rows and document bytes remain in
the existing named object volume. Any deterministic acceptance fixture must be clearly identifiable
and must not contain secrets or personal data.

## UI / Platform Impact

No intended UI changes. The walkthrough covers desktop, tablet and mobile behavior in the preferred
locale against the existing frontend on port `13000`.

## Observability

Capture HTTP status, typed error codes, timing headers, readiness invariants, provider/model
provenance and clean service logs. Never capture request authorization headers, environment values
or response content that may contain sensitive business data. The operator preflight reports only
whether request/response IDs and output exist, not their values.

## Alternatives Considered

1. Marking acceptance from automated tests was rejected because DEC-020 reserves workflow
   acceptance for the product owner.
2. Waiting only for OpenAI was superseded by explicit product-owner authorization for DeepSeek via
   decision 0016. The OpenAI Responses adapter remains available for later switchback.
3. Recreating volumes was rejected because PostgreSQL and document objects are canonical local data.
