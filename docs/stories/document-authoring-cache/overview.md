# Author Documents with Refresh-Safe Local Drafts

## Current Behavior

Document workspace accepts uploaded PDF, DOCX and editable source files, but a
researcher cannot create a source document directly on the page. Unsaved text
has no persistence because no authoring form exists.

## Target Behavior

Researchers can enter a title, choose an editable UTF-8 source format and type
content directly in Document workspace. The page shows the existing safe
raw/preview experience. Every change is cached under the authenticated user ID
in the current browser and restored after F5.

The draft remains local until the user selects Create document. Creation turns
the draft into a bounded browser `File` and submits it through the existing
`POST /api/v1/documents` upload contract. Cache is removed only after the server
returns success, or when the user explicitly discards it.

## Affected Users

- Owners and researchers who author source documents.
- Users sharing a browser profile, whose drafts must remain identity-scoped.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/editable-document-workspaces.md`
- `docs/decisions/0020-local-document-draft-cache.md`

## Non-Goals

- No server-side collaborative draft.
- No viewer authoring permission.
- No executable preview of HTML or source markup.
- No new publication authority.
