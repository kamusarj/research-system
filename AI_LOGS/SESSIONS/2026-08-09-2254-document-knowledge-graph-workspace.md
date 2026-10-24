# Session Log

## Context

- User request: Complete Document Workspace graph analysis within eight hours: graph every upload,
  deep-link analysis, 150–200-character node summaries, independent AI comparison and promotion
  option, remove the 100 relationship display cap, synchronize hierarchy, and separate the Business
  AI Agents system graph. Run Repository Harness and the project.
- Agent: Codex
- Date/time: 2026-08-09 22:54 Asia/Bangkok

## Work Done

- Files changed: document processing/graph/research API services and schemas; graph projections and
  configuration; document and graph frontend routes/components/i18n/styles; backend/frontend tests;
  story/decision/product docs; Harness records; AI handoff logs.
- Behavior changed: every readable upload now builds an isolated graph regardless of fit score.
  Document nodes return summaries capped at 200 characters and optional provider-provenanced AI
  research with an explicit consistency/difference result. Researchers can prepare a draft graph
  change set from the analysis without direct publication. Relationship/hierarchy share the same
  approved research nodes; the system ontology has a separate route; default graph bounds are 1,000
  nodes and 4,000 edges.
- Commands run: Harness bootstrap/intake/matrix/story/decision commands; focused and full Pytest;
  Ruff lint/task-file format check; ESLint, TypeScript, full Vitest and Next production build;
  focused Playwright; Docker Compose rebuild; readiness/migration/log checks; direct projection
  parity and summary-bound inspection; `git diff --check` and Markdown fence validation.

## Reasoning / Decisions

- Decision: paper-fit remains a promotion-routing signal, not an isolated-analysis gate.
- Decision: AI research enriches derived document nodes and may create/reuse a draft change set;
  validate/review/approve/apply remain mandatory and canonical data never changes during research.
- Decision: hierarchy is derived from approved research relationships, while the canonical Business
  AI Agents ontology is intentionally separate.
- Alternatives considered: direct AI publication, retaining the score-60 graph gate, keeping system
  ontology as the research hierarchy, and removing all resource bounds. Rejected for governance,
  usability, corpus-parity and operational-safety reasons.

## Verification

- Tests/checks: backend focused 31/31 and full 316/316; Ruff lint passed and 13 task Python files are
  formatted; frontend ESLint/TypeScript passed; full Vitest 123/123; Next build produced 15 routes;
  focused desktop Playwright 2/2; Alembic `2d4e6f8a0b13 (head)`; readiness `ready`; fresh service logs
  contained no error signature.
- Result: passed. Runtime projection proof found identical 429-node relationship/hierarchy corpora,
  370 relationship edges, 79 derived hierarchy edges, and a separate 45-node/44-edge system map.
  No serialized document node summary exceeded 200 characters. Harness story completion passed;
  trace #62 achieved the required detailed tier 3/3; drift audit found no orphaned, unverified or
  stale story and no broken tool (seven unrelated historical decision-verification findings remain).

## Known Issues

- Independent AI research uses the configured model's bounded knowledge; it is not live web search
  and does not invent citations. Tool-backed research requires a separately governed provider/citation
  contract.
- Truly short or unsupported legacy node evidence may yield a summary below the approximate
  150-character target; serialization never pads with invented content and always enforces 200 max.
- Neo4j remains an optional manually rebuilt projection; PostgreSQL is the default source of truth.

## Next Agent Notes

- Continue from: the rebuilt local runtime at frontend `http://localhost:13000` and API
  `http://localhost:18000`; inspect documents through `View analysis` and the system map at
  `/graph/system`.
- Watch out for: do not publish AI-prepared graph changes without the existing owner review/apply
  workflow. Preserve unrelated dirty-worktree changes.
- Suggested next command: `docker compose ps -a && curl -fsS
  http://localhost:18000/api/v1/system/readiness | jq '{status, graph}'`.
