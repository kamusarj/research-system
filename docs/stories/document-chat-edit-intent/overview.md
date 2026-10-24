# Overview

## Current Behavior

The contextual Document Brainstorm treats every message as advisory chat. A direct imperative such
as `sửa tên thành Bùi Hoàng Linh` returns prose explaining how to edit and offers generic
Replace/Insert/Append actions. It does not use the existing source-revision-bound patch review, so
the user does not receive the expected complete Original/Proposed Accept/Reject workflow.

## Target Behavior

Natural Vietnamese and English edit imperatives entered in the document chat route to the existing
instant-edit pipeline. The current selection is the target when present; otherwise the whole source
is targeted when it fits the established 20,000-character selection bound. The provider result is
always a pending patch with complete Original/Proposed content and explicit Accept or Reject. The
document remains unchanged until Accept.

Questions, critiques and brainstorming prompts continue through advisory Document Brainstorm.

## Affected Users

- Owners and researchers authoring or editing source documents.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-unified-editor-chat/`
- `docs/stories/document-ai-edit-review/`

## Non-Goals

- No automatic patch acceptance or durable save.
- No provider-side intent-classification call.
- No extension of the existing 20,000-character edit-selection bound.
- No automatic repair of document text the user previously inserted from advisory chat.
