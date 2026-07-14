# Research System Completion Plan

## Goal

Hoàn thiện Research System thành lõi vận hành độc lập trước khi xây Discord bot. Discord sau này
chỉ gửi URL và metadata nguồn vào public intake contract; toàn bộ fetch, extract, classify,
deduplicate, review, publish, search và graph projection thuộc Research System.

```text
Discord/manual/API link
        -> URL intake
        -> safe fetch + extraction
        -> deduplication
        -> structured AI classification
        -> threshold policy / review queue
        -> approved ResearchItem
        -> search + graph projections
```

## Architecture decisions

1. PostgreSQL remains the source of truth. Neo4j and search engines are rebuildable projections.
2. Intake is source-neutral. `source_type=discord` is metadata, not Discord-specific domain logic.
3. Every model provider implements one structured-output contract and validates with Pydantic.
4. Provider keys only come from environment/secret management and are never returned by APIs.
5. AI classification cannot publish low-confidence content without human review.
6. Graph nodes use stable typed keys; projection writes must be idempotent.
7. English and Vietnamese are first-class UI locales; research content keeps its original language.

## Provider strategy

| Provider | Transport | Structured output path |
|---|---|---|
| Mock | In-process deterministic | Tests and zero-config demo |
| Ollama | `/api/generate` | JSON format, locally validated |
| OpenAI | Responses API | `text.format` JSON Schema |
| DeepSeek | OpenAI-compatible Chat Completions | JSON object + prompt/schema validation |
| Google Gemini | `generateContent` | JSON MIME type + response schema |
| OpenRouter | OpenAI-compatible Chat Completions | `response_format=json_schema` |
| Mistral | `/v1/chat/completions` | `response_format=json_schema` + local Pydantic validation |

Provider model names are configuration, not hard-coded business rules. Failed provider calls retain
the intake item with an actionable error and can be retried.

## Knowledge Graph v1 ontology

Nodes:

- `ResearchItem`
- `Concept`
- `Technology`
- `AgentPattern`
- `BusinessDomain`
- `Person`
- `CollectorSource`
- `ResearchGap`

Edges:

- `RESEARCHES`, `USES_TECH`, `IMPLEMENTS_PATTERN`, `APPLIES_TO`, `AUTHORED_BY`
- `COLLECTED_FROM`, `REFERENCES`, `EXTENDS`, `SUPPORTS`, `CONTRADICTS`
- `FILLS_GAP`, `SYNTHESIZED_INTO`

The PostgreSQL projection ships first. A Neo4j adapter later uses uniqueness constraints plus
parameterized `MERGE`/batched `UNWIND`; it never becomes the canonical write path.

## Frontend requirements

- Interactive Cytoscape.js canvas with pan, zoom, fit, layouts and selection.
- Node/edge type legend, search, filters, degree/coverage metrics and details panel.
- Click-through from `ResearchItem` to research detail; ego graph and shortest path remain API-backed.
- Responsive application shell, accessible contrast/focus states and meaningful loading/empty/error states.
- Persistent English/Vietnamese locale switcher across the application.

## Delivery gates

### Gate A - Core intake and provider foundation

- URL submission API and inbox UI.
- SSRF-safe HTTP(S) fetch, clean text extraction, content fingerprint deduplication.
- Structured classification, provenance, retryable status and explicit approve/reject.
- Mock/Ollama/OpenAI/DeepSeek/Gemini/OpenRouter/Mistral registry with configuration status endpoint.

### Gate B - Knowledge graph and bilingual UX

- Typed ontology projection from accepted classifications.
- Interactive network visualization and graph statistics/filtering.
- English/Vietnamese shell and primary workflows.

### Gate C - Operational completeness

- Auth/RBAC, encrypted secret deployment, MinIO binary attachments and background job queue.
- Retry/dead-letter policy, rate limiting, observability, backup/restore and integration/E2E tests.
- Meilisearch/pgvector/Neo4j adapters verified as rebuildable projections.

Current foundation: URL intake now uses a PostgreSQL-backed worker queue with job leases,
exponential retry and explicit dead-letter/manual retry. Redis transport, scheduled collectors,
auth/RBAC, MinIO and production observability remain open.

### Gate D - Discord adapter

- Bot allowlists channel/guild, validates sender and submits URLs to the intake API.
- Idempotency key uses Discord message ID + normalized URL.
- Bot reports accepted/duplicate/review/failed status without owning extraction or graph logic.

## External references

- OpenAI structured outputs: <https://developers.openai.com/api/docs/guides/structured-outputs>
- DeepSeek JSON output: <https://api-docs.deepseek.com/guides/json_mode/>
- Gemini structured outputs: <https://ai.google.dev/gemini-api/docs/structured-output>
- OpenRouter structured outputs: <https://openrouter.ai/docs/guides/features/structured-outputs>
- Mistral structured outputs: <https://docs.mistral.ai/studio-api/conversations/structured-output/custom>
- Neo4j `MERGE`: <https://neo4j.com/docs/cypher-manual/current/clauses/merge/>
- Neo4j Python performance: <https://neo4j.com/docs/python-manual/current/performance/>
- Cytoscape.js: <https://js.cytoscape.org/>
- Next.js i18n option considered: <https://next-intl.dev/>
