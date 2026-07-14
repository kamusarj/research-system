# Research System MVP

Local-first research knowledge base for AI Agents for Business. The implementation follows `Docs/Research System Implementation Plan.md` and keeps PostgreSQL as the production source of truth while allowing SQLite for fast local tests.

## Repository architecture

```text
.
├── apps/
│   ├── api/                 # FastAPI application, migrations, and API tests
│   └── web/                 # Next.js application and shared UI components
├── Docs/                    # Product, architecture, and implementation documents
├── AI_LOGS/                 # Cross-agent handoff, decisions, tasks, and sessions
├── docker-compose.yml       # Local runtime orchestration
├── Makefile                 # Stable development commands
└── README.md                # Repository entrypoint
```

Application code belongs under `apps/`. Root-level files are limited to repository-wide documentation, agent conventions, and development/runtime entrypoints. See `apps/README.md` for module boundaries.

## Run with Docker

Requirements: Docker with Compose.

```bash
cp .env.example .env
docker compose up --build
```

If those host ports are already in use, override them without changing container ports:

```bash
API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 NEXT_PUBLIC_API_URL=http://localhost:18000/api/v1 docker compose up --build
```

- Frontend: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/api/v1/health>

Seed the running API database:

```bash
docker compose exec api python -m app.seed
```

## Run for development

API (uses `apps/api/research.db` unless `DATABASE_URL` is set):

```bash
cd apps/api
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload
```

Web app:

```bash
cd apps/web
npm install
npm run dev
```

## Verification

```bash
make test
make lint
make build
docker compose config -q
```

The test suite covers research lifecycle/versioning, source detection and URL normalization,
approved-only search, validated/limited graph responses, Cytoscape lifecycle and states, AI
provenance, RSS review ingestion, and governed JSONL dataset export.

## Source adapters and graph mode

URL intake detects and normalizes four source families behind one adapter contract:

- GitHub repositories: repository metadata, README, topics, languages, license, stars, recent
  releases, supported manifests, and bounded `docs`/`examples` listings. Set `GITHUB_TOKEN`
  for a higher API rate limit or authorized private-repository access.
- Articles/websites: canonical URL, title/author/date, headings, cleaned main text and bounded
  evidence snippets. Navigation, footer, advertising-side content and scripts are excluded.
- Facebook Reels: URL-only intake with an explicit `needs-transcript` state. The collector does
  not depend on fragile Facebook HTML scraping; transcript timestamp evidence is required later.
- PDFs: binary validation with an explicit `needs-text-layer` state until a text-layer extractor
  is configured. OCR is intentionally not the default.

The web UI always uses the same validated graph API contract. Select the backend provider with:

```env
GRAPH_DATA_PROVIDER=postgres  # default rebuildable PostgreSQL projection
GRAPH_DATA_PROVIDER=mock      # empty contract-valid development provider
GRAPH_DATA_PROVIDER=neo4j     # isolated adapter boundary; currently returns 501 after config
```

`GRAPH_DEFAULT_NODE_LIMIT`, `GRAPH_MAX_NODE_LIMIT`, `GRAPH_MAX_EDGE_LIMIT`,
`GRAPH_MAX_DEPTH`, and `GRAPH_MAX_NEIGHBORS` enforce bounded graph queries. Neo4j remains an
upgrade target: selecting it never falls back silently or displays fake graph data.

## Architecture notes

- API paths are stable under `/api/v1`.
- PostgreSQL stores canonical records, outbox events, and the durable intake job queue.
- URL intake returns a queued submission; the Compose `worker` claims jobs with a lease, retries
  transient failures with exponential backoff, and moves exhausted/permanent failures to
  `dead-letter` for explicit retry.
- Search and graph are rebuildable database projections in the MVP; the typed graph repository
  boundary keeps Neo4j as an isolated, explicit upgrade target.
- The deterministic mock AI provider is the default. Set `AI_PROVIDER=ollama` and configure the Ollama URL/model to use local inference.
- Cloud provider adapters include OpenAI, DeepSeek, Gemini, OpenRouter, and Mistral. Their API keys
  are read only from environment variables; use `MISTRAL_API_KEY` and optionally
  `MISTRAL_MODEL` for Mistral.
- RSS collection still runs synchronously on manual request. It preserves source, run, evaluation, and ingestion provenance.
- Training data cannot be accepted until PII, policy, and provenance checks pass.
- Gap detection turns low-coverage graph concepts into a reviewable workspace. Deep-research
  requests create drafts and cannot be approved until a human submits them for review.

## Current boundaries

Production SSO, Kubernetes/cloud deployment, multi-source crawlers, an autonomous deep-research
agent, trend/failed-search gap signals, weekly digests, and model fine-tuning are intentionally
deferred by the plan.
