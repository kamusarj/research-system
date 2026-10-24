# Session Log

## Context

- User request: Brainstorm upgrade requirements for paper suitability scoring, per-upload document graphs, parent/child node display, the main Business AI Agents graph structure, and a ChatGPT brainstorming flow that adds knowledge to the graph.
- Agent: Codex
- Date/time: 2026-07-18 09:17 +0700

## Work Done

- Files changed: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and this session log.
- Behavior changed: None; this was a research and product-design session only.
- Commands run: Read required AI handoff/task/decision files; inspected relevant Research System architecture, completion, MVP and brainstorm documentation; inspected current graph schemas, projection service, frontend types and node detail panel; consulted current OpenAI developer documentation and primary knowledge-graph standards.

## Reasoning / Decisions

- Decision: Recommend two complementary graph views rather than forcing the whole graph into a tree: hierarchy mode for direct parent/child concept and document-structure edges, and relationship mode for citations, support/contradiction, technology, pattern and business-domain links.
- Reason: Taxonomy relations and document containment are hierarchical, while research evidence and implementation relationships are many-to-many.
- Decision: Treat every uploaded document and every chatbot graph update as a draft mutation set; only accepted mutations enter the published canonical projection.
- Reason: This preserves the locked rules that PostgreSQL is canonical, graph is rebuildable, approved knowledge is published, and AI does not overwrite human fields.
- Alternatives considered: Direct AI writes to the canonical graph and a single force-directed view. Both were rejected as the default recommendation because they make ontology drift, duplicate concepts and unsupported claims harder to control.

## Verification

- Tests/checks: Read-only code/schema inspection plus official documentation review; no application tests were needed because no code or product documentation changed.
- Result: The proposed direction is compatible with the current `{nodes, edges, meta}` contract but requires new hierarchy/document/mutation schemas and workflow endpoints before UI implementation.

## Next Agent Notes

- Continue from: Convert this brainstorm into a concrete acceptance specification only after the product owner confirms the ontology pillars, scoring weights and approval thresholds.
- Watch out for: The old brainstorm section suggests unconditional AI auto-ingest, but current accepted decisions require governed approval and prohibit AI overwriting human fields.
- Suggested next command: `sed -n '1,180p' apps/api/app/schemas/graph.py && sed -n '1,145p' apps/api/app/services/graph.py`
