# Gate C Production Observability

## Current Behavior

The API exposes process timing headers and slow-request warnings, while the API
and worker otherwise use conventional unstructured Python logs. There is no
request correlation identifier or Prometheus scrape contract. PostgreSQL
`AuditEvent` records already preserve selected product actions.

## Target Behavior

- API requests receive a safe correlation ID and return it in `X-Request-ID`.
- API and worker logs are JSON objects with an explicit allowlist of fields.
- Operational logs never include request bodies, credentials, document content,
  chat content, arbitrary headers, or raw query strings.
- The API exposes bounded-label Prometheus metrics only when explicitly enabled,
  and the scrape route requires a configured bearer secret.
- PostgreSQL audit records remain the authoritative business audit trail.

## Affected Users

- Operators diagnosing API and background-job failures.
- Developers validating latency and reliability regressions.
- Security reviewers checking that operational telemetry does not leak content.

## Affected Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `Docs/Research System Completion Plan.md`
- `README.md`

## Non-Goals

- Bundling Prometheus, Grafana, Loki, or a hosted observability vendor.
- Replacing product audit events with stdout logs.
- Exporting raw business identifiers or content as Prometheus labels.
- Providing an unauthenticated worker metrics listener.

