# Design

## Domain Model

Compilation is ephemeral: one bounded UTF-8 source produces either one PDF or a typed error. No
source, log or PDF is persisted.

## Application Flow

The browser debounces draft changes and posts source to `/documents/latex/compile`. The API runs
XeLaTeX in a fresh temporary directory, then streams the bounded PDF. The browser owns and revokes
the object URL.

## Interface Contract

- `POST /api/v1/documents/latex/compile`
- JSON request: `{ "source": string }`, capped at 200,000 characters.
- Success: `application/pdf`.
- Errors: typed 422 compile failure, 503 compiler unavailable, 504 timeout.

## Data Model

No tables, objects or migrations.

## UI / Platform Impact

Compiled PDF replaces heuristic output on supporting browsers. Safe text fallback remains visible
with a status message when PDF compilation fails.

## Observability

Only typed outcome, duration and request size may be logged; source and compiler logs are not.

## Alternatives Considered

1. Continue mapping custom macros: rejected because it cannot reproduce TeX layout.
2. Client-side TeX WASM: rejected because package/font compatibility is insufficient for this CV.
