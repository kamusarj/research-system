# Session Log

## Context

- User request: audit the existing Research Intelligence System, then continue implementation through feasible phases with normalized source adapters, human review workflow, bounded graph API, lifecycle-safe Cytoscape UI, tests and documentation.
- Agent: Codex.
- Date/time: 2026-07-13 23:57 Asia/Saigon.

## Work Done

- Files changed:
  - Root runtime/docs: `.env.example`, `docker-compose.yml`, `Makefile`, `README.md`.
  - Backend: `app/core/config.py`, `app/main.py`, `app/api/graph.py`, `app/api/research.py`, `app/schemas/graph.py`, `app/schemas/source.py`, `app/services/graph.py`, `app/services/ingestion.py`, `app/services/research.py`, and the new `app/services/sources/` package.
  - Backend tests: `tests/test_sources.py`, `tests/test_research.py`.
  - Frontend routes/styles: dashboard, ingestion, research list/detail, graph page, `globals.css`, and `lib/i18n.tsx`.
  - Frontend graph modules: `hooks/use-knowledge-graph.ts`, `hooks/use-graph-selection.ts`, `lib/knowledge-graph/*`, and `components/knowledge-graph/*`.
  - Frontend test foundation: `package.json`, `package-lock.json`, `vitest.config.ts`, `vitest.setup.ts`, and graph page/canvas/mapper tests.
- Behavior changed:
  - Added a normalized source contract and URL detection/canonicalization.
  - GitHub extraction now collects bounded repository metadata, README, topics, languages, license, stars, releases, manifests and important docs/examples listings.
  - Article extraction removes structural noise and retains canonical metadata, headings and bounded evidence snippets.
  - Facebook Reels stop at `needs-transcript`; PDFs stop at `needs-text-layer`; neither path pretends extraction succeeded.
  - Graph responses now use validated nodes/edges/meta, hard limits, filters, search, bounded traversal and neighbor expansion.
  - Added `postgres`, `mock`, and explicit Neo4j provider boundaries without UI contract changes.
  - Refactored graph UI into focused modules; Cytoscape now has one instance, position-preserving updates, bounded relayout behavior, responsive resize and cleanup.
  - Added graph loading/empty/error/retry/truncation states, filters, legend, node/edge details, evidence, hide and expand controls.
  - Added research all/review/published/rejected tabs and reject/resubmit transitions. Existing `approved` remains the published/searchable/graph-visible state.
  - API no longer returns raw exception messages for unhandled server errors.

## Reasoning / Decisions

- Decision: keep PostgreSQL as canonical storage and default graph provider; Neo4j remains an isolated projection adapter.
- Reason: this preserves the accepted architecture and existing working workflow while making the UI/provider contract upgradeable.
- Decision: map `approved` to the current published state instead of introducing a duplicate `published` database status.
- Reason: search and graph already project approved items; a new status would require a risky migration and duplicated transitions.
- Decision: use explicit pending states for Reel/PDF rather than brittle scraping or fake extraction.
- Alternatives considered: a separate project, a full schema rewrite, immediate Neo4j dependency, Facebook HTML scraping, default PDF OCR, and a monolithic graph component were rejected as incompatible with project constraints.

## Verification

- Baseline before edits: 16 backend tests pass; Ruff, ESLint, TypeScript, Next.js build and Compose config pass.
- Final backend: `python -m pytest` -> 23 passed, one existing TestClient deprecation warning.
- Final backend lint: `python -m ruff check .` -> pass.
- Final frontend: `npm test` -> 5 passed; `npm run lint`, `npm run typecheck`, and `npm run build` -> pass.
- Dependency install audit: 0 vulnerabilities.
- Compose: `docker compose config -q` -> pass.
- Runtime: health and `/`, `/ingestion`, `/research`, `/search`, `/graph`, `/gaps`, `/collector`, `/training` return HTTP 200 on ports 18000/13000.
- Live graph: 8 unique nodes, 4 edges, zero dangling edges; neighbor query returns valid bounded meta.
- Browser skill check: no in-app browser session was available, so visual QA could not run.

## Known Issues

- Neo4j provider is a deliberate scaffold: unconfigured returns 503 and configured returns 501 until the real idempotent adapter is implemented.
- PDF text-layer extraction and Reel transcript/timestamp submission are not implemented yet; their states are explicit in API/UI.
- Visual responsive and bilingual QA remains open because the in-app browser runtime returned no available sessions.
- The FastAPI TestClient emits the pre-existing `httpx` deprecation warning.
- Workspace is not recognized as a Git repository despite a `.git` directory, so no Git status/diff was available.

## Next Best Action

1. Perform EN/VI visual QA on the running routes when an in-app browser becomes available.
2. Implement and integration-test the Neo4j adapter behind `GraphRepository` without changing the graph API/UI contract.
3. Add PDF text-layer extraction and user-provided Reel transcript evidence with timestamps.
