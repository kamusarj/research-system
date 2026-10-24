# Design

## Domain Model

No domain-model change is planned. Frontend fixes must continue to consume existing typed API contracts and preserve role-aware behavior.

## Application Flow

The sweep follows the current route map and existing browser interactions. Each discovered defect is attributed to a route, shared component, client state boundary, API presenter or responsive style before editing.

## Interface Contract

- Existing frontend routes and API request/response shapes remain stable.
- Expected typed API errors remain user-visible states rather than console exceptions.
- Internal navigation remains keyboard accessible.
- No raw provider/server error may be exposed by a new fix.

## Data Model

No database, migration or persisted application-data change is authorized.

## UI / Platform Impact

All Next.js application routes, shared shell/components and desktop/tablet/mobile Chrome profiles are in audit scope. Any changed user-visible copy must remain bilingual EN/VI.

## Observability

Browser proof captures console errors, page errors, failed same-origin API responses, route HTTP status and overflow. Runtime container logs are scanned only to distinguish frontend defects from backend failures.

## Alternatives Considered

1. Rely on the green unit suite. Rejected because the prior uploaded-document defect existed despite green direct-route tests.
2. Blindly refactor all frontend code. Rejected because it would increase regression risk without evidence.
3. Limit the sweep to the Document workspace. Rejected because the owner explicitly requested all frontend errors.
