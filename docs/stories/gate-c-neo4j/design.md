# Design

## Domain Model

PostgreSQL remains the only canonical model. A Neo4j projection contains `ResearchProjectionNode`
nodes and `RESEARCH_PROJECTION_EDGE` relationships, each identified by the composite
`(projection, graph_id)` key. The `projection` value is either `relationship` or `hierarchy`.

Graph response payloads are validated with the existing `GraphNode` and `GraphEdge` schemas before
they are serialized into Neo4j. Queryable scalar properties are stored separately; the complete
validated payload is stored as bounded JSON so nested provenance/evidence remains contract-safe.

## Application Flow

1. The owner invokes `POST /api/v1/graph/rebuild`.
2. The API builds both full projections from the current PostgreSQL transaction.
3. The Neo4j adapter validates node/edge payloads and checks every edge endpoint.
4. The adapter ensures composite uniqueness constraints.
5. One managed write transaction upserts bounded batches for both views and deletes stale rows.
6. The adapter queries projection counts and returns parity evidence to the owner.
7. Neo4j reads use one managed read transaction, parameterized filters and `limit + 1` sentinel
   rows to preserve existing truncation behavior.

The managed write callback is idempotent because the official driver may retry it after transient
failures. It performs no PostgreSQL writes, file operations or external side effects.

## Interface Contract

- Existing `GET /api/v1/graph` query parameters and response schema remain unchanged.
- Existing node, neighbor, search and stats routes keep their response contracts.
- `POST /api/v1/graph/rebuild` remains owner-only and returns provider plus per-view node/edge
  counts. PostgreSQL mode remains a no-external-write count/rebuild operation.
- Neo4j configuration errors and service failures return typed 503 responses without URIs,
  usernames, passwords or raw driver text.
- Invalid stored projection JSON returns a typed 503 rather than unvalidated graph data.

## Data Model

Neo4j owns only rebuildable rows:

- `(:ResearchProjectionNode {projection, graph_id, payload_json, ...bounded scalars})`
- `[:RESEARCH_PROJECTION_EDGE {projection, graph_id, payload_json, ...bounded scalars}]`

Composite uniqueness constraints protect node and relationship identities. A rebuild upserts all
current rows and prunes rows whose `sync_id` differs, within the same transaction. No PostgreSQL
migration or canonical row update is required.

## UI / Platform Impact

No frontend contract changes. Neo4j is an optional Compose profile with no published host ports.
The API continues to run on PostgreSQL by default; an operator explicitly selects Neo4j after a
successful rebuild. Passwords support the existing `/run/secrets/neo4j_password` precedence.

## Observability

Rebuild logs contain provider, outcome, duration and per-view counts only. They never contain graph
payload bodies or credentials. Service/auth failures are mapped to a bounded error code. Product
audit remains PostgreSQL authoritative; a projection rebuild does not impersonate a business
knowledge edit.

## Alternatives Considered

1. Query PostgreSQL while merely labeling responses `neo4j` was rejected as a fake adapter.
2. Delete-and-recreate in multiple transactions was rejected because readers could see a partial
   graph and failures could erase the last usable projection.
3. Dynamic relationship labels were rejected; a fixed relationship type plus validated `type`
   property keeps Cypher parameterized and preserves the API ontology.
4. Write-through Neo4j updates were rejected because they would create a second canonical path.
5. Automatic rebuild on every canonical mutation was deferred; Gate C requires a verified
   rebuildable adapter, while durable outbox-driven projection scheduling is separate work.
