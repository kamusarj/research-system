# Session: Full-stack defect sweep (frontend, backend, database)

Date: 2026-07-27 00:30 +07
Agent: Claude Code (Opus 5)
Harness intake #20 / story `US-FULLSTACK-DEFECT-SWEEP`

## User Request

Keep going until everything is finished; find and fix defects across frontend, backend and
database.

## Method

The completion goal was already implemented and green, so this pass looked for defects the
existing tests could not see: migration behaviour on the other supported dialect, live
database integrity, API contract edge cases, and test-suite determinism. Seven defects were
found. Three were in code written earlier the same day.

## Defects Found and Fixed

### 1. `alembic upgrade head` failed on SQLite (critical)

`b6d9f1a3c527` added a foreign key with `op.create_foreign_key`, which SQLite cannot do.
It had been applied to PostgreSQL and looked fine, but any SQLite deployment — including
`scripts/verify_migrations.sh` and a fresh developer setup — was broken. Rewritten to use
`batch_alter_table`, matching the precedent in `0b7d2e4f6a18`.

### 2. Two URLs redirecting to one page crashed the worker

`link_submissions.url` is unique. On detecting a duplicate the worker still assigned the
shared canonical URL to the second row, violating that index. The `IntegrityError` became a
retryable `DATABASE_ERROR` and the job retried until its attempt budget ran out. A
shortener, a tracking wrapper or an http/https pair reaches this on ordinary use. The
submitted address is now kept when the canonical one already belongs to another row, which
also records which link a person actually sent.

### 3. Five foreign keys had no index

`research_tags.tag_id` is the one that already hurt: the primary key is
`(research_id, tag_id)`, and a composite index only serves lookups starting at its leading
column. Search and related-research both go the other way, from a tag to its research, and
had nothing to use — the table showed 816 sequential scans. Migration `c7e2a5b8d431` adds
indexes for all five; the live database now reports zero unindexed foreign keys.

### 4. Duplicates recorded before the column existed had no origin

`b6d9f1a3c527` added `duplicate_of_id` without backfilling, leaving the four live rows it
existed to explain still unexplained. Migration `d8f3b1c6a247` backfills them. The first
attempt excluded originals that are currently rejected and matched nothing — every one of
the four duplicated a source rejected afterwards. A backfill answers "what did this row
duplicate when it was recorded", so current status is not consulted. All four are now
linked, including a DOI that resolves to the same arXiv paper.

### 5. Backlog counts returned as floats

`BulkLinkReviewResult.backlog` was typed `dict[str, float]` to accommodate the confidence
threshold, so Pydantic coerced every count. `/backlog` returned `0`, bulk-review returned
`0.0`, and a caller would render "0.0 sources are waiting for a decision". Replaced with a
`ReviewBacklog` model holding integer counts and one float threshold, used by both.

### 6. An unknown status filter returned an empty list

`GET /ingestion/links?status=complete` (a typo for `completed`) answered `200 []`, which is
indistinguishable from "no data". The parameter is now a `Literal` of the real states and a
typo is refused.

### 7. The E2E suite was flaky

`fullyParallel: false` only serialises within a file; six workers still raced across files
against one shared backend, and a run failed on an API error that did not reproduce.
`workers: 1` makes it deterministic — two consecutive full runs pass. The spec added
earlier also hardcoded `localhost:13000` instead of using `baseURL`; fixed, and the whole
suite now runs against `E2E_BASE_URL`.

## Also Corrected

- A refetch race in the provider preflight: flipping the flag changes the React Query key,
  so calling `refetch()` in the same handler re-ran the *previous* key.
- Bulk review only caught `HTTPException`, so an unexpected failure on one item would abort
  the whole batch — the opposite of what the endpoint promises. Every item now fails
  independently, reporting the exception type and never its message.

## Verification

- 250 backend, 33 Discord gateway, 66 frontend tests (349 total)
- 39 Playwright cases across three viewports, twice, deterministically
- `alembic check` reports no drift; downgrade/upgrade round trip passes on SQLite
- Live PostgreSQL at head `d8f3b1c6a247`: zero duplicates without origin, zero unindexed
  foreign keys, zero approved-without-research, zero stuck jobs, zero dangling graph edges
- ruff, eslint, tsc and the production build are clean
- API and worker images rebuilt; live functional test confirmed a 404 source fails as
  `SOURCE_NOT_FOUND` rather than a generic error, and bulk approval produced a link change
  set automatically

## Known Issues

Unchanged from the previous session: conditional-GET validators are not persisted between
submissions, and host rate limiting is per worker process. Both are recorded in
`AI_LOGS/TASKS.md` under Later.

## Next Best Action

Owner decisions only: the two pending change sets, the OpenAI credential, and a Discord
token plus channel allowlist.
