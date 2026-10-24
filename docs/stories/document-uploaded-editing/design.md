# Design

## Domain Model

- Source formats remain editable source documents.
- A PDF/DOCX workspace has an immutable uploaded original (version 1) plus optional editable UTF-8
  derivative versions.
- `source_version=1` for a binary workspace means the original extraction is the current editable
  baseline; any later version is stored UTF-8 text and is never labelled as PDF/DOCX bytes.
- The original object stays reachable through the attachment and initial version records.

## Application Flow

1. The content query returns current editable text. For a binary version 1 it uses the bounded
   canonical extracted text; for later versions it reads the current UTF-8 derivative object.
2. The browser displays the original PDF inline when supported, otherwise offers the original
   download, and labels the editable text as an extracted derivative.
3. Manual or reviewed AI edits use the existing optimistic version check and immutable version
   history.
4. A binary derivative is stored as UTF-8 Markdown-compatible text with a non-binary object suffix.
5. Reprocessing detects a binary workspace whose source version is greater than one and extracts
   the derivative as text rather than attempting to parse it as the original container.
6. Restoring version 1 re-extracts the preserved original and creates a new derivative version.

## Interface Contract

- `GET /api/v1/documents/{id}/content` adds representation metadata and exposes editable extracted
  text for successfully extracted PDF/DOCX workspaces.
- Existing `POST /api/v1/documents/{id}/versions` accepts the derivative text with the same bounded
  optimistic-concurrency contract.
- `GET /api/v1/documents/{id}/original` streams the immutable initial upload with bounded inline or
  attachment disposition.
- Existing errors remain typed; binary documents without readable extracted text return a
  non-editable content contract and cannot create an empty derivative.

## Data Model

No schema migration is required. Existing records already distinguish the immutable initial upload
(`DocumentSourceVersion.version_number=1`, `origin=upload`) from later versions. The attachment keeps
the original object key for PDF/DOCX; the workspace current object key advances to derivative
versions. Historical objects are retained under the accepted version-retention rule.

## UI / Platform Impact

- Document detail renders the editor for readable PDF/DOCX uploads.
- A prominent notice says the user is editing extracted text and the original layout remains
  unchanged.
- PDF originals can be viewed in an embedded browser preview; DOCX keeps the safe extracted preview
  plus original download.
- Desktop/tablet/mobile layouts remain bounded by the existing document workbench.

## Observability

- Existing `document.source.versioned` audit and outbox events record version, origin, hash and size
  without document content.
- Original-file reads do not log bodies or object keys.

## Alternatives Considered

1. Overwrite PDF/DOCX bytes with plain text. Rejected because the filename/MIME would lie and the
   original layout/data would be lost.
2. Build a byte-faithful Office/PDF editor. Rejected for this slice because full document-part,
   font, pagination, form and embedded-object fidelity requires a dedicated editor stack.
3. Keep binary documents read-only. Rejected because it does not meet the owner-requested uploaded
   document workflow.
