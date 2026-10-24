# Design

## Domain Model

The existing revision-bound instant patch remains unchanged. Client feedback classifies an error as
retryable only for network failures and typed 500/502/503/504 provider or proxy failures.

## Application Flow

1. The browser posts the exact selection through the Next.js same-origin proxy.
2. The proxy keeps the connection open beyond the API's configured AI deadline.
3. The API returns a patch or a typed provider/response error; malformed list/object payload access
   is normalized to `AI_RESPONSE_INVALID` instead of escaping as HTTP 500.
4. The hook maps known codes to localized copy and retains the exact last action only for an
   explicit Retry button. A retry creates a fresh revision snapshot and remains conflict-safe.
5. The compact authoring screen keeps the editor and AI visible; preview details expand on demand.

## Interface Contract

- No successful request/response shape changes.
- Error codes used by the client: `AI_EDIT_NO_CHANGE`, `AI_PROVIDER_UNAVAILABLE`,
  `AI_PROVIDER_AUTH_FAILED`, `AI_PROVIDER_RATE_LIMITED`, `AI_RESPONSE_INVALID`, plus transient
  untyped 5xx/network failures.
- Proxy timeout default: 125,000 ms, optionally deployment-overridable.

## Data Model

No migration or durable data change.

## UI / Platform Impact

- Compact header and cache state.
- Preview is a collapsed disclosure containing existing Raw/Preview/Side-by-side modes.
- No separate upload-policy card.
- Retry feedback remains inside the editor and stacks on narrow viewports.

## Observability

Existing request/provider timing and typed status logs remain authoritative. Document content and
provider response bodies remain excluded.

## Alternatives Considered

See decision 0028.
