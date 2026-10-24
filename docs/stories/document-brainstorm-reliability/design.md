# Design

## Domain Model

A failed brainstorm attempt stores a local retry snapshot containing the exact user message and the
bounded conversation history from before that message. It is ephemeral component state.

## Application Flow

1. Send appends one visible user message and captures its pre-request history.
2. A successful response appends one assistant message and clears retry state.
3. A typed provider/transport failure maps to localized safe copy and retains the retry snapshot.
4. Retry sends the saved question with current document source/selection and the saved pre-request
   history; it does not append another user message.
5. No response mutates the document without an existing explicit Apply action.

## Interface Contract

The existing `POST /api/v1/documents/brainstorm` request/response contract is unchanged. Existing
typed `CHAT_PROVIDER_UNAVAILABLE`, `CHAT_PROVIDER_RATE_LIMITED` and `CHAT_PROVIDER_FAILED` errors
are interpreted by the browser instead of displaying their internal message.

## Data Model

No schema or persistence changes. Failed questions and retries remain browser component state.

## UI / Platform Impact

The existing error notice gains localized text and a Retry button at every supported viewport.

## Observability

Existing provider duration/outcome and request status telemetry remains authoritative. Document
source, questions and provider response bodies remain excluded from logs.

## Alternatives Considered

1. Automatically retry timeout failures: rejected because provider calls may cost money and can
   duplicate completed-but-disconnected work.
2. Increase the deadline beyond 120 seconds: rejected because it extends a poor wait and can exceed
   the aligned frontend proxy budget.
3. Display raw provider errors: rejected because they are unstable internal diagnostics.
