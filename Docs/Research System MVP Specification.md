# Research System MVP Specification

This document turns `Research System Implementation Plan.md` into the concrete contract used by the local-first implementation.

## Product scope

The MVP lets a small research team create Markdown research, move it through review, discover approved knowledge, inspect its graph, enrich it with an AI provider, ingest RSS items, and curate exportable training examples.

Out of scope: production SSO, cloud deployment, Kubernetes, a fine-tuning runner, multi-source crawling, and autonomous deep research.

## Research lifecycle

Allowed transitions are:

```text
draft -> in-review -> approved -> archived
   ^          |
   +----------+
```

Updates to an existing item always create a version snapshot. Archived records are soft-deleted and remain addressable by ID. Human-edited summary and tags are only changed by explicit API input; AI results are stored separately until accepted.

## Required metadata

- Required: `title`, `type`, `collection_method`.
- Optional: `summary`, Markdown `content`, `source_url`, `authors`, `tags`, arbitrary JSON `metadata`.
- Types: `internal-research`, `reference`, `deep-research-report`.
- Collection methods: `manual`, `auto-collected`, `ai-researched`.

Authentication and RBAC are deferred. The approve endpoint represents an authorized researcher action in this local single-team MVP.

## Search and graph behavior

- Default library/search results exclude archived items.
- Search matches title, summary, content, authors, and normalized tags case-insensitively.
- Filters compose with pagination and support status, type, collection method, tag, and creation date.
- Graph projection contains approved research nodes, normalized tag/concept nodes, author nodes, collector-source nodes, and manual research relations.
- The graph is rebuilt from the primary database on every request in the MVP and can later be projected into Neo4j.

## AI behavior

- `mock` is the deterministic default provider for local use and tests.
- `ollama` is optional and selected through environment configuration.
- Every output stores model/prompt provenance, input hash, JSON output, confidence, and creation time.
- AI enrichment never overwrites a human field automatically.

## Collector behavior

- RSS is the only MVP source adapter.
- A manual run discovers and normalizes entries, deduplicates by source/external ID and URL, evaluates deterministically, and routes entries by configured thresholds.
- Score `>= auto_approve_threshold` is ingested; score below `auto_reject_threshold` is rejected; the rest enters the review queue.

## Training data governance

- Every event/example records provenance.
- Examples require `pii_status` and `policy_status` before acceptance.
- Accepted examples may be assigned to a versioned dataset and exported as JSONL.
- Holdout examples are excluded from synthetic-generation workflows; this MVP does not implement synthetic generation.

## Local acceptance

1. `docker compose up --build` starts PostgreSQL, API, and frontend.
2. API health returns success and frontend can call it.
3. Research draft can be created, submitted, approved, searched, and viewed in graph output.
4. Editing produces a version snapshot.
5. Mock enrichment records provenance and returns suggestions without overwriting research.
6. RSS entries can be reviewed or ingested.
7. A governed training example can be accepted, included in a dataset, and exported as JSONL.
8. Backend tests, frontend lint/type checks, and production build pass.
