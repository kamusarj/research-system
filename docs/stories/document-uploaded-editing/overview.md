# US-DOCUMENT-UPLOADED-EDITING - View and edit uploaded documents

## Status

implemented

## Current Behavior

Uploaded UTF-8 source formats can be viewed and edited through immutable source versions. PDF and
DOCX retain their uploaded bytes and expose only extracted text through the read-only preview, so a
researcher cannot correct or extend their AI-readable content in Document workspace.

## Target Behavior

Every successfully extracted uploaded document can be viewed and edited from its detail workspace.
UTF-8 formats keep their source editor. PDF and DOCX expose the preserved original separately and
open their bounded extracted text as an explicitly labelled editable derivative. Saving creates an
immutable UTF-8 version, reprocesses/RAG-indexes that version, and never overwrites or pretends to
round-trip the original binary layout.

## Affected Users

- Researchers and owners who curate uploaded documents.
- Viewers who inspect the safe preview and preserved original.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/editable-document-workspaces.md`
- `docs/decisions/0039-loss-safe-binary-document-editing.md`

## Non-Goals

- Byte-faithful PDF or DOCX layout editing.
- In-browser Microsoft Word or PDF authoring.
- Replacing, deleting, or rewriting the original uploaded object.
- Collaborative multi-user merge editing.
