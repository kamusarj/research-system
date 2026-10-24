# US-GRAPH-HIERARCHY Owner-aligned Main Graph

## Status

implemented

## Lane

normal

## Product Contract

The main `/graph` workspace opens as a deterministic parent/child hierarchy matching the product
owner's sketch: the Business AI Agents system root appears at the left, canonical system sections
and deeper concepts proceed in columns to the right, and child branches fan out from visible node
connection points. The force-directed relationship network remains available as a secondary view.

This presentation must expose the existing Graph Intelligence workflow rather than replacing it:
paper-fit evaluation decides whether an uploaded source belongs in the system, each accepted upload
has an isolated document graph, canonical nodes retain parent placement under the system ontology,
and governed chat proposals remain draft graph change sets until human approval and apply.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`

## Acceptance Criteria

- `/graph` defaults to hierarchy mode and loads the canonical root branch.
- Hierarchy nodes use readable cards in left-to-right depth columns with curved parent/child edges
  and explicit connection points; hierarchy mode does not run a force simulation.
- Focusing a child keeps its ancestor path visible and loads a bounded descendant branch.
- The existing relationship network remains selectable and preserves node selection across modes.
- The main hierarchy remains bounded, zoomable, fit-to-screen and responsive.
- Regression proof covers deterministic horizontal placement, default view, mode switching and the
  existing paper-fit/document-graph/placement/chat-proposal contracts.
- The rebuilt local runtime serves the corrected `/graph` without console/API 500 errors and keeps
  the canonical graph invariant-valid.

## Design Notes

- Commands: no new operator command.
- Queries: bounded `GET /api/v1/graph?view=hierarchy&root_node_id=...&depth=2` follows hierarchy
  edges from parent to descendants; ancestor context comes from the ontology breadcrumb.
- API: response shape unchanged; focused hierarchy traversal no longer treats parent edges as
  undirected relationship edges.
- Tables: unchanged.
- Domain rules: PostgreSQL remains canonical; UI layout cannot alter graph data.
- UI surfaces: `/graph` renderer, hierarchy layout, toolbar and focused tests.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Horizontal hierarchy layout and page default/mode behavior. |
| Integration | Existing backend paper-fit, document graph, ontology placement and graph-chat proposal tests. |
| E2E | `/graph` renders the hierarchy on the running desktop/tablet/mobile workspace. |
| Platform | Compose frontend rebuild plus direct/proxied health and graph readiness. |
| Release | Frontend lint, typecheck, test and production build; focused backend regression. |

## Harness Delta

Intake #15 records the owner correction. No new architecture decision is required because the
accepted Graph Intelligence plan already mandates a tree/layered hierarchy without force
simulation; this story aligns the implementation with that contract.

## Evidence

- Frontend lint and TypeScript pass; all 29 Vitest tests pass and the 15-route Next.js production
  build succeeds.
- Focused browser proof passes 15 document-upload/document-graph/hierarchy/chat-proposal/change-review
  cases across desktop, tablet and mobile; the dedicated hierarchy test asserts the default view,
  horizontal card ordering and curved hierarchy edge.
- Ruff passes and 41 focused backend tests cover paper-fit, document processing/isolated graph,
  ontology/directional hierarchy, graph change review/apply and governed graph-chat proposals.
- Live owner-mode browser proof starts with 12 cards (`System → 11 pillars`), focuses
  `Data, Knowledge & Memory` through its output port, keeps the root breadcrumb, loads a bounded
  17-card descendant branch, excludes sibling pillars and emits no console/page error.
- Rebuilt API/frontend runtime returns direct/proxied HTTP 200; readiness is valid at 45 canonical
  nodes / 32 edges, the database is healthy and fresh service logs contain no traceback, exception,
  fatal or HTTP 500 entry.
- The configured DeepSeek provider passed the secret-safe live preflight. A real graph-scoped
  brainstorm safely rejected an ungrounded proposal; a clean document-scoped follow-up created
  review change set `5759af2f-4685-4cfa-b360-39d7981a1fa4` with one evidence-supported valid
  mutation and zero errors or warnings. Governance kept it unapplied.
