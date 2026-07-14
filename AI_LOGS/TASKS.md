# Task Board

## Now

- [ ] Reproduce and fix the multiple user-reported errors after the Docker rebuild.
  - Start with `/graph`, `/ingestion`, `/research`, browser console/network requests, and action flows rather than HTTP status-only checks.
  - Do not resume Neo4j/PDF/Reel feature work until the current UI/runtime is accepted as stable.
- [ ] Review bilingual dashboard, link intake, research review tabs and interactive graph UX in an in-app browser when a browser session is available.

## Next

- [ ] Implement the idempotent Neo4j read/write projection adapter behind the existing graph repository contract.
- [ ] Add a PDF text-layer extractor and user-supplied Reel transcript/timestamp workflow.
- [ ] Add production authentication, RBAC and secret deployment.

## Later

- [ ] Extend background processing to scheduled collectors and add optional Redis transport.
- [ ] Add more collector adapters after RSS is validated.
- [ ] Add production observability, backup and deployment hardening.
- [ ] Add MinIO binary attachment storage when authorized.
- [ ] Replace lightweight search/graph projections with Meilisearch/pgvector and Neo4j when needed.
- [ ] Build Discord bot only after Research System completion gates pass.

## Blocked

- [ ] Exact user-visible error symptoms are not yet captured in logs or reproducible through the existing HTTP smoke checks.
  - Current evidence: the user reports many errors after rebuild, while route status and basic API health checks pass.
  - Next step: reproduce via real browser interaction and capture console/network/API details.

- [ ] Visual browser QA is unavailable in the current environment.
  - Blocker: the in-app browser runtime reports no available browser sessions.
  - Workaround: component tests and HTTP route smoke pass; repeat visual QA when the browser is available.

- [ ] Default API host port 8000 is unavailable in the current environment.
  - Blocker: unrelated `smart_exam_backend` container owns port 8000.
  - Workaround: use `API_PORT=18000 FRONTEND_PORT=13000` as documented.

## Done

- [x] Rebuild Docker images and recreate the full project stack on ports 18000/13000 after the graph/source/workflow refactor.
- [x] Add normalized GitHub/article/Reel/PDF source adapter contract with safe Reel/PDF pending states.
- [x] Add typed, validated and bounded graph API contract with PostgreSQL/mock/Neo4j provider boundary.
- [x] Refactor graph UI into lifecycle-safe Cytoscape components, filters, legend, details, evidence and neighbor expansion.
- [x] Add research review tabs plus reject/resubmit workflow while mapping approved to the published projection state.
- [x] Add backend graph/source/workflow tests and frontend graph state/lifecycle/dedup tests.
- [x] Fix same-URL intake resubmission to honor the newly selected provider and show clear UI feedback.
- [x] Add Mistral strict structured-output provider with environment-only key configuration.
- [x] Move URL intake processing to a PostgreSQL-backed worker with leases, exponential retry and dead-letter/manual retry.
- [x] Standardize repository layout as `apps/api` and `apps/web`, including runtime commands and architecture docs.
- [x] Phase 0 specification.
- [x] Local foundation and Docker Compose.
- [x] Research CRUD/lifecycle/version/comments/tags/relations/attachments.
- [x] Research frontend library/detail/editor.
- [x] Search and related research.
- [x] Knowledge graph MVP.
- [x] AI enrichment mock/Ollama with provenance and embeddings.
- [x] RSS collector and review queue.
- [x] Training Data Hub foundation and JSONL export.
- [x] Seed data, tests, lint, build, dependency audit and docs.
- [x] Phase 8 foundation: low-coverage detector, persistent gap lifecycle, gap workspace, deep-research draft and human approval gate.
- [x] Configurable Docker CORS override and isolated frontend `.next` named volume.
- [x] Source-neutral URL intake with SSRF guard, extraction, dedup, classification, review and publish.
- [x] Mock/Ollama/OpenAI/DeepSeek/Gemini/OpenRouter provider registry without exposing API keys.
- [x] Typed graph ontology, clusters/stats and Cytoscape.js interactive frontend.
- [x] Persistent EN/VI shell and primary dashboard/intake/graph translations.
- [x] EN/VI translation coverage for research, search, collector, gap, training, detail and form workflows.
