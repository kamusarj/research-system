# Document Draft Autosave Without Manual Discard

## Current Behavior

Document Workspace writes each authoring title, format and content change to an
identity-scoped, bounded `localStorage` draft and restores it after refresh or a
browser restart. The same footer also exposes `Discard local draft`, which can
erase the entire in-progress document immediately.

## Target Behavior

Keep the existing synchronous browser autosave and restoration behavior, but
remove the product action that manually discards the authoring draft. A failed
Create retains the draft. A successful governed Create remains the only normal
product event that clears this pre-create cache before navigation.

## Affected Users

- Owners and researchers authoring documents in `/documents`.
- Users recovering work after an accidental tab close or browser crash.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `docs/decisions/0020-local-document-draft-cache.md`
- `docs/decisions/0041-document-draft-autosave-only.md`
- `docs/stories/document-authoring-cache/`

## Non-Goals

- No server-side or cross-device autosave.
- No new API, database schema, auth or publication behavior.
- No change to uploaded-document version caches.
- No change to success-only clearing after governed creation.

