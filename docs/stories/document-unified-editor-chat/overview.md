# Unified Document Editor and Contextual Brainstorm

## Current Behavior

`/documents` separates direct authoring from immediate upload. Choosing an editable source in the
upload card sends it directly to the server instead of loading it into `Document content`, while
post-upload editing is limited to Markdown/TXT on the detail page. Document-scoped brainstorming
exists only as a link to the separate Brainstorm Chat route, so an author cannot ideate beside the
text currently being written or edited.

## Target Behavior

The Document workspace becomes one authoring surface for typed and imported editable UTF-8 source.
Markdown, TXT, LaTeX, reStructuredText, AsciiDoc and HTML imports populate title, format and
`Document content` locally before the user explicitly creates the document. The same source formats
remain editable after upload through immutable source versions. PDF/DOCX keep their governed binary
upload path and are not presented as byte-faithful rich editors.

A contextual AI brainstorm panel appears beside `Document content` for both unsaved authoring and
uploaded editable workspaces. Each explicit Send transmits bounded, redacted current source,
selection and recent local conversation to the configured graph-chat provider. The response never
mutates text automatically; Replace selection, Insert at cursor or Append are separate local user
actions. Creating/saving the resulting source continues through existing upload/version/RAG rules.

## Affected Users

- Owners and researchers authoring or editing source documents.
- Viewers remain read-only and do not receive AI mutation controls.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `README.md`
- `docs/stories/document-authoring-cache/`
- `docs/stories/document-ai-edit-rag/`

## Non-Goals

- No byte-faithful DOCX/PDF rich-text editing or format round trip.
- No automatic AI write, save, upload, RAG publication or graph publication.
- No server-side persistence of pre-create brainstorm history.
- No weakening of provider redaction, context limits, role checks or CSRF checks.
