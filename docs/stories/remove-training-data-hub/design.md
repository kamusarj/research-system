# Design

## Domain Model

Retire `TrainingEvent`, `TrainingExample`, `TrainingDataset`,
`training_dataset_examples`, `PreferencePair`, and `ModelEvalRun`. No active
domain object may retain a foreign key to these models.

## Application Flow

There is no replacement flow. Requests to former Training Data endpoints fall
through FastAPI routing and return `404`. Requests to `/training` fall through
Next.js routing and render the standard not-found response.

## Interface Contract

Remove all `/api/v1/training/*` endpoints and the `/training` browser route.
Remove their localized labels and actions. Existing unrelated API contracts
remain unchanged.

## Data Model

A new head migration drops tables in foreign-key-safe order:

1. `training_dataset_examples`
2. `model_eval_runs`
3. `training_examples`
4. `preference_pairs`
5. `training_events`
6. `training_datasets`

The downgrade recreates the empty schema and indexes so the newest migration
can be mechanically reversed. Deleted row contents are not recoverable.
Historical migrations remain unchanged so fresh and existing databases follow
the same auditable chain.

## UI / Platform Impact

The generated Next.js route list no longer contains `/training`. Primary
navigation was already removed in the preceding Document Workspace change.

## Observability

Alembic version history records the retirement. No record payload is logged or
copied before deletion.

## Alternatives Considered

1. Hide only the navigation. Rejected because the route, API, and stored data
   would remain active.
2. Keep dormant tables. Rejected because the user explicitly requested removal
   of everything related to Training Data.
3. Rewrite the initial migration. Rejected because it would break migration
   history and make upgrades from existing installations unsafe.
