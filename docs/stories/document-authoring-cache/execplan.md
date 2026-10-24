# Exec Plan

## Goal

Let a researcher create an editable source document directly inside Document
workspace without losing an unsaved draft when the page is refreshed.

## Scope

In scope:

- Direct title, source-format and content entry in `/documents`.
- Safe live raw/preview rendering through the existing source viewer.
- Per-user browser draft persistence and refresh restoration.
- Explicit draft discard and automatic cache clearing after successful creation.
- Creation through the existing governed document upload pipeline.

Out of scope:

- Collaborative editing, server-side autosave or draft synchronization.
- Rich-text/WYSIWYG editing.
- Caching uploaded binary PDF/DOCX content in browser storage.
- Changing document tables, processing jobs or review permissions.

## Risk Classification

Risk flags:

- Audit/security because unsaved document text gains browser retention.
- Public user workflow.
- Existing Document workspace behavior.
- Browser/storage compatibility.

Hard gates:

- Local retention of potentially sensitive source text.

## Work Phases

1. Confirm the existing upload and source-preview contracts.
2. Record retention and ownership boundaries.
3. Add bounded cache helpers and deterministic tests.
4. Add the authoring UI and safe preview.
5. Verify refresh restoration, successful creation and cache clearing.
6. Rebuild the runtime and update Harness/AI handoff evidence.

## Stop Conditions

Pause for human confirmation if:

- The feature requires server-side autosave or a new database schema.
- Draft text would be shared across authenticated users.
- Uploaded markup would need executable browser rendering.
- Existing review or publication gates would be bypassed.
