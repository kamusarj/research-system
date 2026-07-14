# Research System - Architecture Design

> Kiến trúc hệ thống tự host để lưu trữ, thu thập, đánh giá, tìm kiếm và trực quan hóa research của team về **AI Agents for Business** dưới dạng Knowledge Graph.
>
> **Trạng thái:** Draft  
> **Cập nhật:** 2026-07-09  
> **Stack đề xuất:** Next.js | FastAPI | PostgreSQL + pgvector | Neo4j | Meilisearch | Redis | Ollama | MinIO

---

## 1. Product Goal

Hệ thống Research không chỉ là nơi lưu tài liệu. Nó là một research operating system cho team:

- Lưu trữ tập trung mọi research item: internal research, reference, paper, blog, repo, case study, AI-generated deep research.
- Phân biệt rõ nguồn gốc: human-collected, AI-collected, AI-researched.
- Tự động thu thập tài liệu từ nhiều nguồn như arXiv, RSS, GitHub, blog, community, business reports.
- Tự động đánh giá tài liệu theo relevance, quality, novelty, actionability, freshness.
- Tự động enrich tài liệu: summarize, tag, extract concepts, detect relations, generate embeddings.
- Tự động đưa tài liệu đạt ngưỡng vào Knowledge Graph, không cần review từng item.
- Phát hiện knowledge gap và chỉ đưa human-in-the-loop ở các quyết định có giá trị cao: approve deep research, assign researcher, review gap quan trọng.
- Cho phép search, semantic discovery, graph exploration và Q&A trên toàn bộ knowledge base.

---

## 2. Architecture Principles

| Principle | Decision |
|---|---|
| PostgreSQL là source of truth | Mọi research item, metadata, status, audit log và workflow state được ghi vào PostgreSQL trước. |
| Graph là projection | Neo4j phục vụ graph query, visualization, path finding, gap analysis. Không dùng Neo4j làm dữ liệu gốc. |
| Search là projection | Meilisearch và pgvector được rebuild từ PostgreSQL khi cần. |
| Event-driven processing | Create/update/collect item tạo event, worker xử lý graph sync, search index, AI enrichment bất đồng bộ. |
| Idempotent pipeline | Mỗi job có thể chạy lại mà không tạo duplicate node, edge, embedding hoặc attachment. |
| Human-in-the-loop có chọn lọc | AI-collected item đạt threshold tự ingest; con người chủ yếu xử lý gap, low-confidence case và deep research report. |
| Self-hosted first | Mặc định dùng local services: Ollama, sentence-transformers, MinIO, Docker Compose. Có thể thay LLM provider sau qua adapter. |

---

## 3. High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend - Next.js                           │
│ Dashboard | Research Library | Editor | Graph | Search | Collector   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS / WebSocket
┌───────────────────────────────▼─────────────────────────────────────┐
│                         API - FastAPI                                │
│ Research API | Graph API | Search API | Collector API | AI API       │
│ Auth | RBAC | Audit Log | Event Publisher                            │
└───────────────┬──────────────────────────────┬──────────────────────┘
                │                              │
                │                              │ enqueue events
                │                              ▼
┌───────────────▼────────────────────┐  ┌─────────────────────────────┐
│              Data Layer             │  │ Background Workers           │
│ PostgreSQL + pgvector - truth        │  │ Collector Workers            │
│ Neo4j - knowledge graph              │  │ Evaluation Workers           │
│ Meilisearch - full-text search       │  │ Enrichment Workers           │
│ Redis - queue/cache/pubsub           │  │ Graph/Search Sync Workers     │
│ MinIO - files and attachments        │  │ Gap Detection Workers         │
└───────────────┬────────────────────┘  └──────────────┬──────────────┘
                │                                      │
                └──────────────────┬───────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AI Runtime                                  │
│ Ollama LLM | sentence-transformers | PDF/HTML extraction             │
│ Playwright/Browserless | Source adapters                             │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.1. Repository Topology

The implementation uses a deployable-app monorepo layout:

```text
.
├── apps/
│   ├── api/                  # FastAPI, persistence, migrations, API tests
│   └── web/                  # Next.js routes, UI components, API client
├── Docs/                     # Product and technical source documents
├── AI_LOGS/                  # Cross-agent operational handoff
├── docker-compose.yml        # Local service orchestration
├── Makefile                  # Stable repository commands
└── README.md                 # Setup and architecture entrypoint
```

Deployable services belong under `apps/`. Repository-wide entrypoints stay at the root so local commands remain short and stable. A future `packages/` directory should only be introduced for code genuinely shared by multiple deployables; infrastructure-specific files can move under `infrastructure/` once Compose is no longer the only deployment target.

---

## 4. Core Domain Model

### 4.1. Research Item

Research Item là entity trung tâm của hệ thống.

| Field | Purpose |
|---|---|
| `id` | UUID hoặc mã hiển thị dạng `RES-2026-001`. |
| `title` | Tên research, paper, blog, repo hoặc report. |
| `type` | `internal-research`, `reference`, `deep-research-report`. |
| `status` | `draft`, `in-review`, `approved`, `archived`, `rejected`. |
| `collection_method` | `manual`, `auto-collected`, `ai-researched`. |
| `collector_source_id` | Nguồn tự động nếu có: arXiv, OpenAI Blog, GitHub Trending, RSS. |
| `source_url` | URL gốc. |
| `external_id` | ID từ nguồn ngoài: arXiv ID, GitHub repo full name, RSS GUID. |
| `authors` | Người viết hoặc tác giả ngoài. |
| `summary` | Tóm tắt ngắn, có thể do AI sinh. |
| `content` | Markdown chuẩn hóa để đọc, search, embed và graph extraction. |
| `tags` | Topic, technology, business domain, agent pattern. |
| `evaluation` | Điểm AI và reasoning cho auto-collected item. |
| `provenance` | Dấu vết thu thập: source, run ID, model version, prompt version. |

### 4.2. Knowledge Graph Nodes

| Node | Meaning |
|---|---|
| `ResearchItem` | Một research item cụ thể. |
| `Concept` | Khái niệm như RAG, tool use, memory, evaluation. |
| `Technology` | Framework/tool như LangGraph, CrewAI, AutoGen, pgvector. |
| `AgentPattern` | Pattern như ReAct, Plan-and-Execute, Multi-Agent Debate. |
| `BusinessDomain` | Lĩnh vực áp dụng như customer service, sales, analytics. |
| `Person` | Team member hoặc tác giả ngoài. |
| `CollectorSource` | Nguồn tự động thu thập. |
| `ResearchGap` | Gap do hệ thống phát hiện. |

### 4.3. Knowledge Graph Edges

| Edge | From -> To | Meaning |
|---|---|---|
| `RESEARCHES` | ResearchItem -> Concept | Item nghiên cứu topic này. |
| `USES_TECH` | ResearchItem -> Technology | Item dùng hoặc phân tích công nghệ này. |
| `IMPLEMENTS_PATTERN` | ResearchItem -> AgentPattern | Item triển khai pattern này. |
| `APPLIES_TO` | ResearchItem -> BusinessDomain | Item áp dụng vào domain này. |
| `AUTHORED_BY` | ResearchItem -> Person | Tác giả hoặc contributor. |
| `COLLECTED_FROM` | ResearchItem -> CollectorSource | Nguồn thu thập. |
| `REFERENCES` | ResearchItem -> ResearchItem | Tham chiếu hoặc cite. |
| `EXTENDS` | ResearchItem -> ResearchItem | Mở rộng nghiên cứu trước. |
| `SUPPORTS` | ResearchItem -> ResearchItem | Ủng hộ kết luận. |
| `CONTRADICTS` | ResearchItem -> ResearchItem | Mâu thuẫn hoặc phản biện. |
| `SYNTHESIZED_INTO` | ResearchItem -> ResearchItem | Được tổng hợp vào deep research report. |
| `FILLS_GAP` | ResearchItem -> ResearchGap | Item giúp lấp gap. |

---

## 5. Main System Components

### 5.1. Frontend App

Next.js App Router là UI chính cho team.

| Module | Responsibility |
|---|---|
| Dashboard | Tổng quan activity, graph health, collector health, trending topics, gaps. |
| Research Library | List, filter, sort, saved views, collection badges. |
| Research Editor | Markdown editor, metadata, relations, attachments, version history. |
| Graph Viewer | Interactive graph, filters, clusters, ego graph, shortest path, gap overlay. |
| Search & Discovery | Full-text search, semantic search, related research, Q&A. |
| Collector Manager | Source config, run history, health, thresholds, review queue. |
| Gap Workspace | Danh sách gap, priority, owner, deep research request, approval. |

Recommended UI stack:

- Next.js + TypeScript
- React Query cho server state
- Zustand cho client UI state
- shadcn/ui + Tailwind CSS
- Cytoscape.js cho graph visualization
- Tiptap hoặc Milkdown cho Markdown editor

### 5.2. Backend API

FastAPI chịu trách nhiệm application logic, auth, validation và event publishing.

| Service | Responsibility |
|---|---|
| ResearchService | CRUD research items, status workflow, versioning, attachments. |
| CollectorService | Manage sources, runs, thresholds, discovered item lifecycle. |
| EvaluationService | Score item, explain decision, route auto-approve/reject/review. |
| EnrichmentService | Summarize, extract concepts, generate tags, suggest relations. |
| GraphService | Query graph, ego graph, paths, clusters, gap data. |
| SearchService | Full-text search, semantic search, recommendations. |
| GapService | Detect coverage gaps and create research opportunities. |
| AuditService | Track human and AI actions for traceability. |

### 5.3. Background Workers

Workers xử lý mọi tác vụ chậm hoặc dễ retry.

| Worker | Trigger | Output |
|---|---|---|
| Collector Worker | Schedule/manual run | `discovered_items`, raw content, attachments. |
| Extraction Worker | Discovered item created | Clean Markdown, metadata, fingerprint. |
| Dedup Worker | Extracted item ready | Duplicate decision by URL, fingerprint, semantic similarity. |
| Evaluation Worker | Non-duplicate item ready | Scores, threshold decision, reasoning. |
| Ingestion Worker | Approved item | Research item in PostgreSQL. |
| Enrichment Worker | Research item created/updated | Summary, tags, concepts, embeddings, relations. |
| Graph Sync Worker | Research item changed | Neo4j nodes and edges. |
| Search Index Worker | Research item changed | Meilisearch document and pgvector rows. |
| Gap Detection Worker | Scheduled or graph changed | ResearchGap nodes and suggestions. |
| Digest Worker | Weekly schedule | Team digest and collector summary. |

---

## 6. Data Stores

### 6.1. PostgreSQL + pgvector

PostgreSQL là dữ liệu gốc.

Core tables:

- `research_items`
- `research_versions`
- `research_relations`
- `tags`
- `research_tags`
- `people`
- `research_authors`
- `attachments`
- `collector_sources`
- `collector_runs`
- `discovered_items`
- `evaluations`
- `concepts`
- `research_concepts`
- `research_gaps`
- `audit_events`
- `embedding_chunks`

`pgvector` dùng cho:

- Semantic search.
- Duplicate detection.
- Similar research recommendation.
- Candidate selection trước khi LLM suggest relation.

### 6.2. Neo4j

Neo4j là graph projection phục vụ:

- Graph visualization.
- Path finding giữa concept, technology, research item.
- Cluster detection.
- Graph health metrics.
- Gap detection dựa trên vùng thiếu coverage.

Neo4j được sync từ PostgreSQL. Nếu Neo4j mất dữ liệu, có thể rebuild từ PostgreSQL.

### 6.3. Meilisearch

Meilisearch phục vụ UX search nhanh:

- Typo-tolerant full-text search.
- Facets theo `type`, `status`, `collection_method`, `source`, `tags`, `date`.
- Autocomplete title, tag, technology.

### 6.4. Redis

Redis dùng cho:

- Celery/RQ task queue.
- Job locks để chống duplicate processing.
- Cache cho graph query nặng.
- Pub/Sub cho realtime activity.
- Rate limit cho API và collector.

### 6.5. MinIO

MinIO lưu file binary:

- PDFs tải từ paper sources.
- Images, notebooks, datasets.
- Raw imported files.
- Exported reports.

PostgreSQL chỉ lưu metadata và object key.

---

## 7. Collector Architecture

### 7.1. Source Adapter Interface

Mỗi nguồn thu thập được implement như một adapter cùng interface.

```python
class CollectorAdapter(Protocol):
    source_key: str

    async def discover(self, since: datetime | None) -> list[DiscoveredCandidate]:
        ...

    async def fetch(self, candidate: DiscoveredCandidate) -> RawDocument:
        ...

    async def normalize(self, raw: RawDocument) -> NormalizedDocument:
        ...
```

Adapter ban đầu:

| Adapter | Method | Notes |
|---|---|---|
| arXiv | API | Papers, authors, abstract, PDF. |
| RSS | Feed parser | OpenAI, Anthropic, LangChain, LlamaIndex blogs. |
| GitHub | API | Repos, README, stars, topics, release activity. |
| Web Page | Playwright + trafilatura | Blogs/case studies không có RSS. |
| Hacker News | API | Discussions and trend signal. |

### 7.2. Auto-Collector Flow

```text
Scheduled run / Manual run
        │
        ▼
Discover candidates from source
        │
        ▼
Fetch raw content and attachments
        │
        ▼
Normalize to Markdown + metadata
        │
        ▼
Deduplicate
  ├─ URL/external_id match
  ├─ content fingerprint match
  └─ semantic similarity match
        │
        ▼
AI evaluation
  relevance + quality + novelty + actionability + freshness
        │
        ├─ score >= auto_approve_threshold -> ingest
        ├─ score <= auto_reject_threshold  -> reject with reason
        └─ otherwise                       -> review queue
        │
        ▼
Enrichment + graph sync + search indexing
```

### 7.3. Threshold Policy

| Decision | Default Rule |
|---|---|
| Auto-approve | Overall score >= 80 and relevance >= 75 and duplicate confidence < 0.85. |
| Needs review | Overall score 50-79 or any important field has low confidence. |
| Auto-reject | Overall score < 50 or duplicate confidence >= 0.95. |
| Deep research approval | Always requires human approval before publish. |

Thresholds are configured per source. Example: arXiv can have lower review burden than random blogs because metadata quality is higher.

---

## 8. AI Processing Architecture

### 8.1. AI Tasks

| Task | Input | Output |
|---|---|---|
| Summarization | Clean content | Short summary and key takeaways. |
| Concept extraction | Title, summary, content | Concepts, technologies, patterns, domains. |
| Tagging | Extracted concepts | Normalized tags. |
| Evaluation | Normalized document + source metadata | Scores and reasoning. |
| Relation suggestion | New item + similar candidates | Typed relations with confidence. |
| Gap detection | Graph clusters + coverage metrics + trend signals | ResearchGap items. |
| Q&A | User question + retrieved context | Answer with citations to research items. |
| Deep research | Approved gap + context bundle | Draft deep research report. |

### 8.2. Model Runtime

Default local runtime:

- Ollama for LLM inference.
- sentence-transformers for embeddings.
- Optional reranker model for search quality.

Model access should sit behind an `LLMProvider` interface:

```python
class LLMProvider(Protocol):
    async def complete_json(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...
```

This keeps the system self-hosted by default while allowing later providers without rewriting domain logic.

### 8.3. Provenance Requirements

Every AI output should store:

- `model_name`
- `model_version`
- `prompt_version`
- `input_hash`
- `output_json`
- `confidence`
- `created_at`

This is required because evaluation and graph extraction will affect the knowledge base automatically.

---

## 9. Data Lifecycle

### 9.1. Manual Research Lifecycle

```text
Draft
  │
  ▼
In review
  │
  ├─ request changes -> Draft
  │
  ▼
Approved
  │
  ├─ edit -> new version + async re-enrichment
  └─ archive -> Archived
```

Manual research can be edited by team members. Approved items are indexed and shown in the graph by default.

### 9.2. AI-Collected Lifecycle

```text
Discovered
  │
  ▼
Fetched
  │
  ▼
Normalized
  │
  ▼
Deduplicated
  │
  ▼
Evaluated
  │
  ├─ Auto-rejected
  ├─ Needs review
  └─ Auto-approved
          │
          ▼
       Ingested as ResearchItem
          │
          ▼
       Enriched + Indexed + Graph synced
```

AI-collected items do not require review if they pass policy thresholds. The dashboard must make these decisions visible and auditable.

### 9.3. Gap Lifecycle

```text
Detected
  │
  ▼
Prioritized
  │
  ├─ Assign to human researcher
  ├─ Request AI deep research
  └─ Snooze / dismiss
        │
        ▼
Deep research draft
        │
        ▼
Human review
        │
        ▼
Published report fills gap
```

---

## 10. API Surface

### 10.1. Research

```text
GET    /api/v1/research
POST   /api/v1/research
GET    /api/v1/research/{id}
PUT    /api/v1/research/{id}
DELETE /api/v1/research/{id}
POST   /api/v1/research/{id}/submit-review
POST   /api/v1/research/{id}/approve
POST   /api/v1/research/{id}/archive
GET    /api/v1/research/{id}/versions
GET    /api/v1/research/{id}/relations
POST   /api/v1/research/{id}/relations
POST   /api/v1/research/{id}/attachments
```

### 10.2. Search and Discovery

```text
GET    /api/v1/search?q=
POST   /api/v1/search/semantic
GET    /api/v1/search/suggest?q=
GET    /api/v1/research/{id}/related
POST   /api/v1/qa
```

### 10.3. Graph

```text
GET    /api/v1/graph
GET    /api/v1/graph/node/{id}
GET    /api/v1/graph/ego/{id}
GET    /api/v1/graph/path?from=&to=
GET    /api/v1/graph/clusters
GET    /api/v1/graph/gaps
GET    /api/v1/graph/stats
POST   /api/v1/graph/rebuild
```

### 10.4. Collector

```text
GET    /api/v1/collector/sources
POST   /api/v1/collector/sources
PUT    /api/v1/collector/sources/{id}
POST   /api/v1/collector/sources/{id}/run
GET    /api/v1/collector/runs
GET    /api/v1/collector/runs/{id}
GET    /api/v1/collector/review-queue
POST   /api/v1/collector/review-queue/{id}/approve
POST   /api/v1/collector/review-queue/{id}/reject
POST   /api/v1/collector/review-queue/{id}/edit-and-approve
GET    /api/v1/collector/stats
```

### 10.5. AI and Gaps

```text
POST   /api/v1/ai/summarize
POST   /api/v1/ai/extract-concepts
POST   /api/v1/ai/suggest-relations
POST   /api/v1/ai/evaluate
POST   /api/v1/gaps/{id}/assign
POST   /api/v1/gaps/{id}/request-deep-research
POST   /api/v1/deep-research/{id}/approve
```

---

## 11. Database Design

### 11.1. Core PostgreSQL Tables

```sql
CREATE TABLE research_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_id TEXT UNIQUE,
    title TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('internal-research', 'reference', 'deep-research-report')),
    status TEXT NOT NULL CHECK (status IN ('draft', 'in-review', 'approved', 'archived', 'rejected')),
    collection_method TEXT NOT NULL CHECK (collection_method IN ('manual', 'auto-collected', 'ai-researched')),
    source_url TEXT,
    external_id TEXT,
    summary TEXT,
    content TEXT,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE collector_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    schedule_cron TEXT,
    auto_approve_threshold NUMERIC NOT NULL DEFAULT 80,
    auto_reject_threshold NUMERIC NOT NULL DEFAULT 50,
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE discovered_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES collector_sources(id),
    run_id UUID,
    external_id TEXT,
    source_url TEXT,
    title TEXT NOT NULL,
    raw_content_key TEXT,
    normalized_markdown TEXT,
    fingerprint TEXT,
    status TEXT NOT NULL,
    duplicate_of UUID REFERENCES research_items(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, external_id)
);

CREATE TABLE evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discovered_item_id UUID REFERENCES discovered_items(id),
    research_item_id UUID REFERENCES research_items(id),
    overall_score NUMERIC NOT NULL,
    relevance_score NUMERIC NOT NULL,
    quality_score NUMERIC NOT NULL,
    novelty_score NUMERIC NOT NULL,
    actionability_score NUMERIC NOT NULL,
    freshness_score NUMERIC NOT NULL,
    decision TEXT NOT NULL,
    reasoning TEXT,
    model_name TEXT,
    prompt_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE research_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES research_items(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES research_items(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    discovered_by TEXT NOT NULL CHECK (discovered_by IN ('manual', 'ai')),
    confidence NUMERIC,
    reasoning TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, target_id, relation_type)
);

CREATE TABLE embedding_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_item_id UUID NOT NULL REFERENCES research_items(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (research_item_id, chunk_index)
);
```

### 11.2. Indexing Notes

Required indexes:

- `research_items(status, type, collection_method)`
- `research_items(created_at DESC)`
- `discovered_items(source_id, external_id)`
- `discovered_items(fingerprint)`
- `evaluations(decision, overall_score)`
- `research_relations(source_id, relation_type)`
- `embedding_chunks USING ivfflat (embedding vector_cosine_ops)`

---

## 12. Sync and Consistency

### 12.1. Event Types

| Event | Trigger |
|---|---|
| `research.created` | Manual item created or collector ingests item. |
| `research.updated` | Content/metadata changed. |
| `research.approved` | Item becomes visible in approved corpus. |
| `research.archived` | Item removed from default views. |
| `collector.run.started` | Collector source run starts. |
| `collector.item.discovered` | Candidate found. |
| `collector.item.evaluated` | Evaluation completed. |
| `gap.detected` | New or updated ResearchGap. |

### 12.2. Projection Strategy

```text
PostgreSQL transaction commits
        │
        ▼
Outbox event row created
        │
        ▼
Worker reads outbox
        │
        ├─ Sync Neo4j projection
        ├─ Sync Meilisearch projection
        ├─ Generate/update embeddings
        └─ Publish realtime notification
```

Use an outbox table instead of fire-and-forget Redis publish for important events. Redis can still be the queue transport, but PostgreSQL outbox gives retry safety.

---

## 13. Security and Governance

### 13.1. Roles

| Role | Permission |
|---|---|
| Admin | Manage sources, thresholds, users, rebuild indexes, approve deep research. |
| Researcher | Create/edit manual research, review assigned gaps, approve review queue if allowed. |
| Member | Read/search/comment, suggest relations, flag items. |
| Viewer | Read-only access. |

### 13.2. Governance Rules

- Every AI-created or AI-modified field must be traceable through audit events.
- Auto-approved collector items must show score, source, model, and reason in UI.
- Deep research reports require human approval before becoming approved research.
- Source adapters run with rate limits and per-source failure isolation.
- Attachments are scanned/validated by MIME type and size before storage.

---

## 14. Observability

Track system health from three angles.

### 14.1. Product Metrics

- Total research items by type and collection method.
- Approved vs rejected auto-collected items.
- Topic coverage by cluster.
- Gaps detected, assigned, filled.
- Search queries with no good result.

### 14.2. Pipeline Metrics

- Collector runs by source.
- Items discovered/fetched/normalized/evaluated/ingested.
- Evaluation score distribution.
- Duplicate rate.
- Worker latency and retry count.

### 14.3. System Metrics

- API latency and error rate.
- Worker queue depth.
- Neo4j sync lag.
- Meilisearch indexing lag.
- Ollama inference latency.
- Disk usage for MinIO and databases.

Recommended stack:

- Prometheus + Grafana for metrics.
- Structured JSON logs.
- OpenTelemetry traces for collector and AI pipeline.

---

## 15. Deployment Architecture

### 15.1. Local/Self-Hosted Docker Compose

Core containers:

- `frontend` - Next.js
- `api` - FastAPI
- `worker` - background workers
- `scheduler` - collector schedules
- `postgres`
- `neo4j`
- `meilisearch`
- `redis`
- `ollama`
- `minio`
- `browserless`
- `caddy`

### 15.2. Environment Boundaries

| Environment | Purpose |
|---|---|
| Local dev | Small sample data, hot reload, optional mocked LLM. |
| Staging | Full pipeline test with selected sources. |
| Production | Scheduled collectors, backups, monitoring, stable model versions. |

### 15.3. Backup Strategy

- PostgreSQL: daily logical backup + point-in-time recovery if possible.
- Neo4j: backup optional because it is rebuildable, but useful for fast restore.
- Meilisearch: rebuildable from PostgreSQL.
- MinIO: must be backed up because PDFs and attachments are original assets.
- Config and prompts: version-controlled.

---

## 16. Implementation Roadmap

### Phase 1 - Foundation

- Setup Docker Compose.
- Implement PostgreSQL schema and migrations.
- Build Research CRUD API.
- Build basic Next.js dashboard, research list, detail, editor.
- Add auth and roles.
- Add MinIO attachments.

### Phase 2 - Search and Graph

- Add Meilisearch indexing.
- Add pgvector embeddings and semantic search.
- Add Neo4j projection sync.
- Build graph viewer with filters, node detail, ego graph.
- Add manual relation management.

### Phase 3 - AI Enrichment

- Add Ollama provider interface.
- Add summarization, concept extraction, tagging.
- Add relation suggestion based on semantic candidates.
- Store AI provenance and audit events.
- Add Q&A over approved research.

### Phase 4 - Auto-Collector

- Build source adapter interface.
- Implement arXiv, RSS, GitHub and generic web page adapters.
- Add scheduler and collector run history.
- Add extraction, dedup, evaluation and threshold policy.
- Add collector manager UI and review queue.
- Auto-ingest approved items into research library and graph.

### Phase 5 - Gap Intelligence

- Add graph coverage metrics.
- Detect topic gaps from graph topology, trend signals and failed searches.
- Build gap workspace.
- Add deep research workflow with human approval.
- Add weekly digest.

---

## 17. Recommended MVP Scope

For the first useful version, avoid building the full system at once.

MVP should include:

- Manual research CRUD with Markdown.
- PostgreSQL source of truth.
- Meilisearch full-text search.
- Basic pgvector semantic search.
- AI summarization and tagging.
- Neo4j graph projection with ResearchItem, Concept, Technology, CollectorSource.
- One reliable collector: arXiv or RSS.
- Evaluation threshold and auto-ingest.
- Dashboard showing recent research, collector health and top gaps.

Defer until after MVP:

- Multi-source community scraping.
- Full deep research agent.
- Advanced graph algorithms.
- Complex collaboration workflow.
- SSO/Keycloak if basic auth is enough for the first team deployment.
