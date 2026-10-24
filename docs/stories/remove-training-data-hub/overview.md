# Remove Training Data Hub

## Current Behavior

The application exposes a Training Data Hub at `/training` and an API under
`/api/v1/training/*`. Six PostgreSQL tables store events, examples, datasets,
dataset membership, preference pairs, and model evaluation runs. The live
database contains one example, one dataset, and one membership row.

## Target Behavior

Training Data is no longer an active product capability. The page, API,
authorization rules, ORM schema, seed records, tests, and current product-plan
commitments are removed. A new Alembic head migration deletes the six tables
and their existing rows.

Historical migrations and agent/session logs remain intact because they are
audit history, not active product behavior. The new migration is the
authoritative retirement boundary.

## Affected Users

- Local owners and researchers who could capture or export training examples.
- Operators applying database migrations.

## Affected Product Docs

- `README.md`
- `Docs/Research System Implementation Plan.md`
- `AGENTS.md`
- `docs/decisions/0019-remove-training-data-hub.md`

## Non-Goals

- No replacement dataset-building workflow.
- No data export or backup.
- No changes to document-scoped AI chat or graph evaluations.
