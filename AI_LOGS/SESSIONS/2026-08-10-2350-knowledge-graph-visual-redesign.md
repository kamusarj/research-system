# Session Log

## Context

- User request: Research existing knowledge-graph visual patterns and redesign the current graph,
  which rendered hierarchy incorrectly and the relationship view as an unreadable hairball.
- Agent: Codex
- Date/time: 2026-08-10 23:50 +07

## Work Done

- Files changed: `apps/web/app/graph/page.tsx`, `apps/web/app/graph/page.test.tsx`,
  `apps/web/app/globals.css`, `apps/web/components/knowledge-graph/d3-graph-canvas.tsx`,
  `apps/web/components/knowledge-graph/graph-toolbar.tsx`,
  `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`,
  `apps/web/lib/knowledge-graph/hierarchy-layout.ts`,
  `apps/web/lib/knowledge-graph/graph-visualization.ts`, their focused tests,
  `apps/web/e2e/graph-hierarchy.spec.ts`, `apps/web/lib/i18n.tsx`,
  `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`, this story packet and AI logs.
- Behavior changed: hierarchy renders only connected parent/child knowledge as a readable
  multi-column branch atlas and reports unplaced approved nodes; relationship retains the complete
  bounded corpus with semantic label budgeting, importance sizing and selected-neighborhood focus.
  The canvas now owns the page, while filters/legend and inspection appear only when requested.
- Commands run: Harness bootstrap/intake/story/matrix; frontend ESLint, TypeScript, full and focused
  Vitest, production build; focused Playwright on desktop/tablet/mobile; live browser audit against
  real data; Docker frontend rebuild/recreate; health/readiness/log checks; `git diff --check`.

## Reasoning / Decisions

- Decision: use progressive disclosure and semantic zoom instead of attempting to display every
  hierarchy card and every relationship label at equal prominence.
- Reason: live evidence showed 429 relationship nodes and only 91 nodes connected by hierarchy
  edges. The old hierarchy compressed a shallow forest into a nearly invisible line, while equal
  relationship labels created a hairball.
- Alternatives considered: showing all 338 hierarchy-unplaced nodes as roots was rejected because
  it invents visual structure; changing API/schema or auto-applying parent relations was rejected
  because the request is visual and canonical publication remains governed.

## Verification

- Tests/checks: frontend 31 files / 130 tests; focused story proof 28 tests; ESLint; TypeScript;
  15-route production build; Playwright 6/6 across desktop/tablet/mobile; live 1440/1024/390 px audit;
  direct/proxied health, readiness, graph HTTP 200 and fresh container-log scan.
- Result: all pass. Live relationship keeps 429 nodes with 26 overview labels; hierarchy shows 91
  connected nodes and reports 338 unplaced. All audited viewports have zero page overflow and zero
  browser errors. Runtime is live on frontend `13000` and API `18000`.

## Known Issues

- The 338 approved nodes without `PARENT_OF` / `BROADER_THAN` placement remain a source-data
  curation gap. They remain available in relationship/search and are not hidden from the corpus.
- Default API port `8000` remains occupied by the unrelated `smart_exam_backend`; this project uses
  the documented `18000` API / `13000` frontend override.

## Next Agent Notes

- Continue from: product-owner visual review at `http://localhost:13000/graph`.
- Watch out for: do not mistake unplaced hierarchy nodes for deleted data; no corpus row changed.
- Suggested next command: review or propose governed parent/child placements for the 338 unplaced
  nodes if the owner wants denser hierarchy coverage.
