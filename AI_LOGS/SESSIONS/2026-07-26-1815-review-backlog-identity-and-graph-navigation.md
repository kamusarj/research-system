# Session: Review backlog, graph identity and hierarchy navigation

Date: 2026-07-26 18:15 +07
Agent: Claude Code (Opus 5)

## User Request

Continue the completion goal loop recorded as Harness intake #19.

## Work Completed

Goal areas A2, A3, A4, A5, C1, C2, C3, C4, C5.

### Review backlog and duplicates (A2, A5)

- `GET /api/v1/ingestion/links/backlog` reports what is waiting on a person, including the
  auto-approve confidence threshold that was previously a server-side secret.
- `POST /api/v1/ingestion/links/bulk-review` decides the whole queue or a named batch, and
  reports each outcome separately so one bad item cannot discard the rest of the decisions.
- Duplicate matching no longer treats a *rejected* submission as an original: rejection is
  a judgement about one record, not a permanent ban on the material.
- New `link_submissions.duplicate_of_id` column (migration `b6d9f1a3c527`). A duplicate of
  an unpublished original now records what it duplicates and inherits the research record
  when that original is approved, instead of being stranded with a null `research_id`.
- The live database has four such stranded duplicates; they are now visible and recoverable.

### Projection staleness (A4)

- Applying a change set records `graph.canonical.changed`; rebuilding a projection records
  `graph.projection.rebuilt`. `GET /api/v1/graph/projections` reports which derived copies
  are behind. Rebuilds stay an explicit owner action rather than being triggered inside
  `apply`, which would make a governed local operation depend on three external services.

### Graph identity (A3)

- `canonical_node_index` matches relationship-view taxonomy labels against approved
  `KnowledgeNode` records and their aliases. A matched concept now carries the canonical
  ID in both views, so a selection survives switching between them and the classifier's
  wording is preserved as an alias rather than becoming a second node.

### Hierarchy navigation (C1, C2, C4)

- The hierarchy is drawn around a focus node rather than always the root. Any node with
  children can be opened at any depth; pillars still unfold in place as compound boards.
- Breadcrumb entries navigate to the ancestor they name. Previously every crumb ran the
  same collapse handler regardless of position.
- The inspector's browse action is hidden for leaf nodes, and a child named in the
  inspector that is not yet drawn is navigated to rather than ignored.

### Truncation and metrics (C3, C5)

- `GraphMeta` gained `total_node_count`, `total_edge_count` and `node_limit`. The UI says
  "Showing 40 of 111 matching nodes" with a Show more control, instead of a warning that
  something unspecified was hidden.
- Header metrics now always describe what is drawn, with the wider total shown beside them
  rather than in their place.
- `graph_max_node_limit` raised 100 to 300 and the edge limit 250 to 700, so paging has
  room to reach the end of a large branch.

## Files Changed

Backend: `app/models.py`, `app/api/ingestion.py`, `app/api/graph.py`, `app/api/search.py`,
`app/schemas/ingestion.py`, `app/schemas/graph.py`, `app/services/ingestion.py`,
`app/services/graph.py`, `app/services/graph_changes.py`, `app/core/config.py`,
`app/services/projection_state.py` (new),
`migrations/versions/b6d9f1a3c527_link_duplicate_origin.py` (new).

Frontend: `app/graph/page.tsx`, `app/ingestion/page.tsx`, `app/globals.css`, `lib/types.ts`,
`lib/i18n.tsx`, `lib/knowledge-graph/types.ts`,
`components/knowledge-graph/node-details-panel.tsx`,
`components/intake/review-backlog.tsx` (new), `components/intake/submission-list.tsx`.

Tests: `test_intake_review_backlog.py` (new), `test_graph_identity.py` (new),
`review-backlog.test.tsx` (new), additions to `app/graph/page.test.tsx`.

## Commands and Results

- `apps/api/.venv/bin/python -m pytest` — 215 passed (from 202)
- `apps/api/.venv/bin/python -m ruff check .` — clean
- `npm test` in `apps/web` — 48 passed (from 41)
- `npx tsc --noEmit`, `npm run lint` — clean
- `alembic upgrade head` applied `b6d9f1a3c527` to the live PostgreSQL database
- Live checks on API `18000`: backlog reports 4 duplicates awaiting their original;
  hierarchy meta reports `total_node_count` 12 against a limit of 5; relationship meta
  reports 40 of 111.

## Known Issues

- Zero relationship nodes currently reconcile with the ontology, because the approved
  research classifications and the seeded ontology labels do not yet overlap. The
  behaviour is proven by tests; it will take effect as the ontology grows.
- Remaining goal work: C6-C12 (rendering, empty states, filters, accessibility,
  search-to-focus), E2 provider preflight, all of D (Discord bot), B10, B13, E3-E5.

## Next Best Action

Goal task 9: graph rendering, empty-pillar guidance, view-appropriate filters,
search-to-focus and keyboard accessibility across three viewports.
