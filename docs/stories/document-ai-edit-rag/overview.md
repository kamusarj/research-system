# Inline AI Editing and Automatic Document RAG

## Current Behavior

Uploaded UTF-8 sources can be inspected as raw text and safe preview, but the
document detail page is read-only. The direct-authoring cache exists only before
upload. Document-scoped chat can retrieve pgvector chunks when an owner has
rebuilt the approved-only search projection; draft uploaded documents otherwise
fall back to a leading text excerpt.

## Target Behavior

Owners and researchers can edit Markdown and TXT sources in the document
workspace. Selecting text opens bounded AI rewrite actions. AI results are saved
as proposals and change nothing until the user explicitly accepts one. Manual
saves, accepted proposals and restores create immutable source versions and
requeue the existing extraction/evaluation/document-graph pipeline.

Every successful extraction also refreshes the current document's pgvector
chunks automatically. Draft document chunks are usable only by that authorized
document scope and remain excluded from approved global search results.

## Affected Users

- Owners and researchers editing source documents or using document-scoped chat.
- Viewers, who retain read-only access to source, version metadata and RAG status.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/editable-document-workspaces.md`
- `docs/stories/document-authoring-cache/`
- `docs/stories/rag-retrieval-quality/`

## Non-Goals

- Rich/WYSIWYG editing of DOCX or PDF.
- Collaborative multi-cursor editing or cross-device autosave.
- Automatic acceptance of AI text or graph changes.
- A new RAG framework, embedding model or vector database.

