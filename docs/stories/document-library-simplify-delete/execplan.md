# Exec Plan

## Goal

Simplify Uploaded documents and add safe editing/deletion actions with a useful summary.

## Scope

In scope:

- Four-column uploaded-document list.
- Bounded document summary.
- Existing editor exposed as Edit.
- Confirmed owner-only single-document deletion.
- API, UI, authorization, and cleanup tests.

Out of scope:

- Bulk actions and trash restore.
- Canonical graph rollback.

## Risk Classification

Risk flags:

- Data loss.
- Authorization.
- Public contracts.
- Existing behavior.

Hard gates:

- Applied graph and intake provenance must not be deleted.
- Non-owners must not receive delete authority.

## Work Phases

1. Record intake and design contract.
2. Add summary and safe delete service/API.
3. Simplify the responsive document table.
4. Add focused backend and frontend tests.
5. Run relevant checks and update Harness/AI logs.

## Stop Conditions

Pause for human confirmation if deletion would need to cascade into applied canonical graph state or
if the existing role policy cannot enforce owner-only access.
