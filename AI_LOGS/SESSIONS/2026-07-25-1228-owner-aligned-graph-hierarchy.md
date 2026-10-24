# Owner-aligned Graph Hierarchy

## Context

- User request: correct the graph to match the supplied sketch and complete all requested Graph
  Intelligence behavior: paper-fit screening, an isolated graph per uploaded document, parent-child
  node display, a canonical system framework for AI placement, and chatbot-assisted graph additions.
- Agent: Codex `/root`.
- Date/time: 2026-07-25 12:28 +0700.

## Work Done

- Audited all five requested workflows against current code, tests, docs and the live runtime.
- Recorded Harness intake #15, human correction intervention #1 and normal story
  `US-GRAPH-HIERARCHY`.
- Made hierarchy the default `/graph` view and kept the force-directed relationship network as a
  secondary switch.
- Replaced hierarchy force simulation with deterministic left-to-right tree placement.
- Rendered readable hierarchy cards with type accents, child counts, input/output connection ports
  and curved parent-child branches.
- Kept the root overview bounded to `System → 11 pillars`; a branch port focuses a bounded
  descendant view while retaining its ancestor breadcrumb.
- Corrected hierarchy API traversal to follow parent-to-child direction. Focused branches no longer
  pull in sibling pillars through the parent edge.
- Reused the existing paper-fit, isolated document graph, ontology placement and governed
  chat-to-draft-change-set implementations; no canonical data or approval rule changed.
- Updated the Graph v2 product contract, README, story packet and AI handoff logs.
- Rebuilt and recreated only API/frontend; preserved PostgreSQL, worker and object data and did not
  touch `smart_exam_*`.
- Rechecked the configured DeepSeek provider after network recovery. The secret-safe preflight
  returned `ready`; real graph-scoped sessions exercised graph context tools and stopped safely
  when broad turns reached the bounded tool-loop limit. An ungrounded draft correctly failed
  validation. A clean document-scoped session then created review change set
  `5759af2f-4685-4cfa-b360-39d7981a1fa4` with one evidence-supported valid mutation and zero errors
  or warnings.

## Files Changed

- Backend: `apps/api/app/services/graph.py`, `apps/api/tests/test_ontology.py`.
- Main graph UI: `apps/web/app/graph/page.tsx`, `apps/web/app/graph/page.test.tsx`,
  `apps/web/app/globals.css`, `apps/web/components/knowledge-graph/graph-toolbar.tsx`,
  `apps/web/hooks/use-knowledge-graph.ts`, `apps/web/lib/i18n.tsx`.
- Graph rendering/mapping/tests: `apps/web/lib/knowledge-graph/d3-graph-renderer.ts`,
  `apps/web/lib/knowledge-graph/hierarchy-layout.ts`,
  `apps/web/lib/knowledge-graph/hierarchy-layout.test.ts`,
  `apps/web/lib/knowledge-graph/graph-mapper.ts`,
  `apps/web/lib/knowledge-graph/graph-mapper.test.ts`,
  `apps/web/e2e/graph-hierarchy.spec.ts`.
- Product/Harness: `README.md`, `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`,
  `docs/stories/graph-horizontal-hierarchy.md`, Harness intake/story/intervention/trace state.
- Handoff: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and this session log.

## Decisions Made

- The sketch means a hierarchy-first mind-map/tree: system root on the left, canonical sections and
  deeper nodes in columns to the right, with branches fanning from explicit node ports.
- Relationship mode remains available because cross-links are useful, but it is not the primary
  system-navigation presentation.
- Hierarchy branch traversal is directional; ancestor context is merged from ontology breadcrumbs
  instead of treating hierarchy edges as undirected relationships.
- Canvas results remain bounded to 16 API nodes plus any missing breadcrumb ancestor; truncation is
  explicit and full direct children remain available through the node inspector/search.
- Chatbot proposals remain drafts requiring validation, owner approval and apply; “self add” does
  not mean bypassing graph governance.

## Commands/Tests Run

- Harness bootstrap, intake #15, normal story lifecycle and human correction intervention.
- `uv run --frozen ruff check app tests`
- Focused backend suite for paper fit, documents, ontology, graph changes and graph chat:
  `41 passed`.
- `npm run lint`, `npm run typecheck`, `npm test`: 29 frontend tests passed.
- `npm run build`: 15 Next.js routes compiled.
- Playwright document upload/processed graph/hierarchy/chat proposal/change review:
  15 passes across desktop/tablet/mobile.
- Live Chrome root/focused-branch interaction and screenshot inspection with console/page-error
  capture.
- API/frontend Docker builds and recreate; direct/proxied health, readiness, service and log checks.
- `python -m app.operations verify-chat-provider`: DeepSeek `deepseek-v4-pro` returned `ready`.
- Real graph- and document-scoped `POST /api/v1/chat/sessions/{id}/messages` turns, followed by
  `GET /api/v1/graph/change-sets/5759af2f-4685-4cfa-b360-39d7981a1fa4`.
- Final change-set check: `needs_review`, one supported valid mutation, zero errors/warnings,
  `approved_by=null`, `applied_at=null`.
- `git diff --check` on the scoped change set.

## Verification Result

- Initial `/graph` displays 12 readable cards: one Business AI Agents root and eleven canonical
  pillars.
- Focusing `Data, Knowledge & Memory` displays the ancestor root, selected pillar and a bounded set
  of descendants only; sibling pillars are absent, breadcrumb is preserved and the UI shows the
  truncation notice.
- Paper-fit, isolated uploaded-document graph, ontology placement and governed chatbot change-set
  workflows pass deterministic backend and cross-viewport browser proof.
- Runtime health is OK; readiness is valid at 45 canonical nodes / 32 edges; database is healthy,
  API/frontend images are current and fresh API/frontend/worker logs have no traceback, exception,
  fatal or HTTP 500 entry.
- Live DeepSeek preflight returns `ready` for `deepseek-v4-pro`. The real follow-up proposal remains
  in `needs_review`, and the canonical graph was not mutated.

## Known Issues

- The broad first DeepSeek turn can consume the five-call tool budget before proposing a mutation;
  the server stops safely with `CHAT_TOOL_LOOP_LIMIT`, and a focused follow-up succeeds. Product
  owner review remains required before any draft is approved or applied.
- `npm audit --omit=dev` currently reports three high-severity production dependency advisories in
  `next`, `postcss` and `sharp`. This session did not perform a breaking or forced dependency update.
- The first Harness completion verifier included production build and exceeded the CLI's ten-second
  command timeout. Build remains separately proven; the mechanical verifier was narrowed to
  lint/typecheck/unit tests and completion then passed.

## Next Best Action

1. Have Linh inspect `http://localhost:13000/graph`, open pillar ports and confirm the visual model.
2. Have Linh inspect change set `5759af2f-4685-4cfa-b360-39d7981a1fa4`, complete the real chat
   walkthrough and record the product-owner decision.
3. Open a maintenance intake to resolve the three current production dependency advisories with
   compatible patched versions and full regression proof.
