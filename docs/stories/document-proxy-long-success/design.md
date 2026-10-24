# Design

## Domain Model

The provider's configured 120-second HTTPX timeout bounds inactivity for an individual network
operation; it is not a total wall-clock deadline. The browser proxy budget is therefore a separate
bounded deployment value informed by observed end-to-end duration.

## Application Flow

1. Browser sends one document edit through the Next.js same-origin rewrite.
2. Next.js keeps the upstream connection alive for 180 seconds by default.
3. API/provider success or a typed API failure reaches the browser before the proxy terminates it.
4. Retry remains an explicit user action after actual transient failures.

## Interface Contract

No API shape changes. `API_PROXY_TIMEOUT_MS` is exposed to the frontend service and defaults to
`180000`; invalid or non-positive values fall back to that bounded default.

## Data Model

No schema, migration, retention or source-version change.

## UI / Platform Impact

No copy or workflow change. A valid slow result reaches the existing Original/Proposed review.

## Observability

Validation correlates frontend socket-reset logs with API provider/request duration and verifies the
effective runtime configuration without logging provider content.

## Alternatives Considered

1. Unlimited proxy timeout: rejected because hung connections need a bound.
2. Keep 125 seconds: rejected by the observed 131.115-second success.
3. Automatic retry: rejected because it can duplicate paid work.
4. Async job conversion: deferred beyond this local instant-edit reliability correction.
