# Exec Plan

## Goal

Let users view and safely edit every successfully extracted uploaded document without losing the
original file or misrepresenting a text derivative as a byte-faithful PDF/DOCX edit.

## Scope

In scope:

- PDF/DOCX editable extracted-text derivatives.
- Immutable versioning, optimistic concurrency, restore, AI edit and reprocessing compatibility.
- Original PDF preview/original download.
- Bilingual disclosure and focused backend/frontend/runtime proof.

Out of scope:

- Binary layout round-trip or direct Office/PDF mutation.
- Original-object deletion or retention pruning.
- New external editor/provider dependencies.

## Risk Classification

Risk flags:

- Data integrity and accidental original overwrite.
- Binary-format/type confusion.
- Version restore and worker reprocessing behavior.
- User-visible editing workflow and authorization.

Hard gates:

- Original uploaded bytes remain unchanged and downloadable after edits/restores.
- Current derivative is processed as UTF-8 text, never as fake PDF/DOCX bytes.
- Empty/unreadable binary extraction remains non-editable.
- Existing UTF-8 source editing behavior does not regress.

## Work Phases

1. Record high-risk intake/story/decision.
2. Add loss-safe binary source reading/version storage rules.
3. Add original-file response and representation metadata.
4. Add bilingual original/derivative UI.
5. Add integration and component tests.
6. Run focused and full relevant proof, rebuild runtime, and record Harness trace.

## Stop Conditions

Pause for human confirmation if implementation would require overwriting original binary objects,
silently changing the accepted upload format, deleting historical versions, or weakening the
existing optimistic/human-review contracts.
