# 0009 Production-Safe Operational Observability

Date: 2026-07-21

## Status

Accepted

## Context

Gate C requires enough operational evidence to diagnose request, provider, and
worker failures, but research documents and chat prompts can contain sensitive
business content. The application already has PostgreSQL audit events and basic
timing headers, but it lacks correlation and a scrape contract.

## Decision

Use correlated JSON stdout logs with a strict field allowlist and bounded-label
Prometheus metrics. Protect `/metrics` with an independently configured bearer
secret and keep it disabled by default. Use route templates and typed outcomes,
never raw paths or business identifiers, as metric labels. Keep PostgreSQL
`AuditEvent` as the authoritative product audit trail.

The API exposes process-local metrics. The worker emits structured job telemetry
but does not open an unauthenticated metrics listener. Cross-process aggregation
belongs to a later deployment-level design if required.

## Alternatives Considered

1. Payload-rich logs were rejected because redaction cannot reliably make arbitrary
   research and chat content safe.
2. An open metrics endpoint was rejected because provider/model availability and
   operational rates are deployment-sensitive.
3. Prometheus multiprocess mode was deferred because shared-file lifecycle and
   container cleanup require a larger deployment contract.

## Consequences

Positive:

- Operators can correlate API failures and measure bounded reliability/latency.
- The default deployment adds no new unauthenticated telemetry surface.
- Audit and operational telemetry have explicit, non-overlapping responsibilities.

Tradeoffs:

- API metrics reset on restart and do not aggregate worker-process counters.
- Operators must provision the scraper, secret injection, TLS/network policy, and
  retention externally.
- A future multi-replica deployment needs aggregation or per-target queries.

## Follow-Up

- Define deployment-level scraping, retention, alert thresholds, and dashboard
  ownership before production rollout.
- Revisit worker metric aggregation only with an authenticated collection design.

