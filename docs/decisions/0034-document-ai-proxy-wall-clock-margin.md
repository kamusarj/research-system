# 0034 Give Document AI Proxy a Wall-Clock Margin

Date: 2026-08-04

## Status

Accepted; amends decision 0028's 125-second proxy value.

## Context

A real DeepSeek edit completed successfully at the API in 131.115 seconds while the 125-second
Next.js rewrite proxy reset the browser socket. HTTPX's configured 120-second timeout bounds network
inactivity rather than total wall-clock duration, so 125 seconds is not a valid end-to-end ceiling.

## Decision

Default `API_PROXY_TIMEOUT_MS` to a bounded 180,000 ms, expose it through Compose and fall invalid or
non-positive configuration back to the same default. Keep Retry explicit and do not introduce an
unlimited connection or automatic provider call.

## Alternatives Considered

1. Disable the proxy timeout: rejected because hung connections must remain bounded.
2. Raise it only to 135 seconds: rejected because five seconds is insufficient operational margin.
3. Automatically retry socket resets: rejected because the first paid request may still complete.

## Consequences

Positive:

- The observed 131.115-second successful edit can reach browser review.
- Operators can set a different positive bound without rebuilding source.

Tradeoffs:

- Failed upstream calls may occupy a proxy connection longer.
- Extremely long provider calls can still exceed 180 seconds and should move to an asynchronous job
  if they become normal.

## Follow-Up

- Reconsider asynchronous document-edit jobs if successful calls repeatedly approach 180 seconds.
