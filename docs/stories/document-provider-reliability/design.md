# Design

## Domain Model

Reuse the existing document workspace, processing attempt, provider provenance and strict
`DocumentGraphAnalysis` schema. No domain or database changes are required.

## Application Flow

1. Send the initial structured document-graph request to the selected provider.
2. Parse and validate the response at the provider boundary.
3. On structured-response validation failure only, build a bounded recovery prompt containing the
   schema validation summary without echoing raw provider output or secrets.
4. Retry once using the same provider, model, response schema and document input.
5. Persist only a schema-valid result; otherwise retain `AI_RESPONSE_INVALID` and the existing
   manual-retry workflow.

## Interface Contract

No route or response-envelope changes. Existing typed error mapping remains authoritative.

## Data Model

No migration. Existing attempt and provider/model provenance records remain the durable source.

## UI / Platform Impact

No UI change. A successful bounded recovery moves the document through the existing graph review
workflow; a failed recovery keeps the existing retry action.

## Observability

Emit a structured warning with document/attempt/provider identifiers and recovery outcome. Do not
log raw document text, provider output, authorization headers or credentials.

## Alternatives Considered

1. Silent cross-provider fallback was rejected because it breaks explicit provider selection and
   obscures provenance.
2. Persisting a partially valid graph was rejected because it weakens graph invariants.
3. Retrying the whole durable job was rejected because provider retry and job retry are separate
   controls and would repeat extraction/evaluation unnecessarily.
