# Design

## Domain Model

Operational telemetry has two distinct surfaces:

1. Product audit events in PostgreSQL remain durable, queryable business evidence.
2. Runtime logs and metrics report operational health without business payloads.

A request ID is an ephemeral correlation value. Incoming values are accepted only
when they match a conservative printable identifier grammar and length bound;
otherwise the API creates a UUID.

## Application Flow

An outer API middleware establishes request context, measures duration, records
bounded HTTP metrics, emits one canonical completion log, and returns the request
ID. The worker configures the same JSON formatter and emits explicit job outcome
events. Existing warnings and exceptions inherit the active correlation ID where
one exists.

## Interface Contract

- Every API response includes `X-Request-ID`.
- `GET /metrics` is excluded from OpenAPI.
- Metrics disabled: HTTP 404.
- Metrics enabled without a configured secret: HTTP 503.
- Missing or incorrect `Authorization: Bearer ...`: HTTP 401.
- Correct bearer secret: Prometheus text exposition.

The endpoint never accepts credentials through a query parameter.

## Data Model

No database schema or migration changes. Prometheus state is process-local and
resets on restart. PostgreSQL `AuditEvent` retention remains governed separately.

## UI / Platform Impact

The browser can use `X-Request-ID` from failed responses when reporting an issue.
Container logs become JSON lines. An external Prometheus scraper must inject the
bearer header over a trusted network; no host scrape port or dashboard stack is
added by this story.

## Observability

Logs use a strict field allowlist and never serialize arbitrary `LogRecord`
attributes. Metric labels are limited to bounded dimensions such as method, route
template, status code, job type, provider, model, operation, outcome, and typed
error code. Raw paths, UUIDs, URLs, user text, document text, response content,
secrets, and exception messages are prohibited as labels.

## Alternatives Considered

1. Prometheus multiprocess files shared by API and worker were rejected for this
   slice because their lifecycle and cleanup rules add deployment coupling.
2. An unauthenticated worker scrape server was rejected because internal network
   placement alone is not a sufficient secret boundary.
3. Logging whole request/response payloads was rejected because research and chat
   content can contain sensitive business data.

