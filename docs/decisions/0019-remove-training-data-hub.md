# 0019 Remove Training Data Hub

Date: 2026-07-30

## Status

Accepted

## Context

The Research System implemented a Training Data Hub with a browser route, API,
authorization rules, seed behavior, and six relational tables. The owner
explicitly requested that everything related to Training Data be removed. The
live database contains one example, one dataset, and one membership row.

Removing only the navigation would leave a reachable feature and retained
data. Rewriting the initial migration would make existing database upgrades
unsafe and erase the audit trail.

## Decision

Retire Training Data as an active product domain. Remove its UI, API,
authorization rules, ORM models, seed behavior, feature tests, and commitments
from current product documentation.

Add a new Alembic head migration that drops all six Training Data tables and
their rows. The downgrade recreates empty tables for schema reversibility but
does not restore deleted row contents.

Keep historical migrations, accepted decisions, AI handoff/session logs, and
the original brainstorm source unchanged as audit history. These artifacts do
not expose or reactivate the feature; the new migration and this decision
supersede their Training Data direction.

## Alternatives Considered

1. Hide the feature while keeping API and data. Rejected because it does not
   satisfy removal.
2. Keep empty dormant tables. Rejected because the tables are part of the
   retired domain.
3. Rewrite all historical records. Rejected because it destroys traceability
   and can break upgrades from deployed revisions.
4. Export a backup before deletion. Rejected because the owner asked for the
   data to be removed, not retained elsewhere.

## Consequences

Positive:

- The active product has no Training Data surface or persisted domain.
- Existing installations converge through an explicit migration.
- Unrelated research and document data remain untouched.

Tradeoffs:

- Existing Training Data rows are permanently deleted.
- Downgrade restores schema only, not data.
- Historical references remain discoverable in audit/source artifacts.

## Follow-Up

- Reintroducing any dataset-building feature requires a new product decision,
  schema, and story.
