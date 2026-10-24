# Design

## Domain Model

`DocumentGraphWorkspace` remains the isolated graph aggregate. Every readable processed source owns
structural nodes, semantic nodes, semantic edges and evidence regardless of paper-fit score.
Paper-fit still controls review priority and promotion guidance, not graph existence.

Each `DocumentGraphNode.metadata` may contain a typed `ai_research` record with provider/model,
bounded independent summary, comparison status (`consistent`, `different`, `insufficient`) and a
bounded difference explanation. Reprocessing clears derived nodes and their research because both
must be regenerated against the current immutable source version.

The canonical knowledge graph remains PostgreSQL-owned and human-governed. AI research enriches a
document graph and may seed a draft `GraphChangeSet`; it never applies mutations.

## Application Flow

1. Upload and extraction produce canonical text and paper-fit evaluation.
2. Any readable text proceeds to document graph extraction; score affects routing only.
3. The graph API emits source summaries normalized to approximately 150–200 characters.
4. A researcher requests independent AI research for one, several or all semantic nodes.
5. One structured provider call returns bounded results keyed to existing node IDs. The service
   rejects unknown/duplicate IDs and stores only validated metadata plus provider provenance.
6. With `create_change_set=true`, the service creates/reuses the existing document-origin draft
   change set after research. Review, approval and transactional apply stay unchanged.
7. Global relationship and hierarchy reads share the same approved relationship projection.
   Hierarchy reverses taxonomy-to-research membership edges into parent-child presentation and uses
   canonical parent links only for nodes present in that corpus.
8. The complete Business AI Agents ontology is read separately as the system map.

## Interface Contract

- Existing `GET /api/v1/documents/{id}/graph` adds typed `ai_research` per node and bounded summary.
- New `POST /api/v1/documents/{id}/graph/research` accepts optional `node_ids` and
  `create_change_set`; returns the refreshed graph and optional draft change set.
- Existing `POST /api/v1/documents/{id}/create-change-set` remains available.
- Existing `GET /api/v1/graph?view=relationship|hierarchy` keeps its shape; both views now represent
  the same approved knowledge corpus.
- New `GET /api/v1/graph/system` returns the canonical Business AI Agents system map.
- Browser `View analysis` links to `/documents/{id}#document-analysis`.
- Browser `/graph/system` renders the separate system map.

Provider/schema, feature flag, authorization, CSRF and typed error boundaries remain in force.

## Data Model

No migration is required. Validated AI research lives in the existing JSON metadata on derived
document nodes and full structured output provenance remains in `ai_outputs`. Reprocessing already
deletes derived nodes, so stale research cannot survive a source-version change.

## UI / Platform Impact

- Document list has separate Open document and View analysis actions.
- Document graph inspector clearly separates document summary, AI research, comparison and evidence.
- Researchers can research one node or research the graph and prepare a reviewed change set.
- Relationship view requests the current safety maximum in one read and no longer exposes the old
  page-count display behavior.
- Knowledge hierarchy and relationship are two layouts of the same corpus.
- Business AI Agents system map is navigated and rendered separately.

## Observability

AI research records provider/model, node count, aggregate input/output hashes and latency without
logging document text or generated content. Audit records contain workspace, node/change-set IDs and
counts only. Runtime failures use typed, secret-free errors.

## Alternatives Considered

1. Publish AI research directly. Rejected because it bypasses graph governance and human authority.
2. Keep the score-60 graph gate. Rejected because it prevents users from analyzing low-fit uploads
   in their isolated workspace even though isolation makes that analysis safe.
3. Store AI research in new relational columns. Rejected for this bounded slice because the record
   is derived/version-scoped and existing node metadata plus `ai_outputs` already provide durable
   typed provenance without a destructive migration.
4. Keep hierarchy as the system ontology. Rejected because relationship/hierarchy then describe
   different datasets. The system ontology remains useful but belongs on its own route.

