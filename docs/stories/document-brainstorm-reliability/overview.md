# Overview

## Current Behavior

Document Brainstorm sends bounded source context to DeepSeek, but a provider timeout is rendered as
the raw internal message `DeepSeek chat request timed out`. The submitted question remains only as
a chat bubble, with no explicit way to retry it. Users must retype or copy the question and may
accidentally create duplicate conversation turns.

## Target Behavior

Document Brainstorm maps provider/transport failures to localized, user-safe feedback and offers an
explicit Retry for retryable failures. Retry reuses the exact failed question and its pre-request
history without adding a duplicate user bubble. No retry is automatic, and responses remain
advisory until the user explicitly applies them.

## Affected Users

- Owners and researchers brainstorming beside editable documents.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-unified-editor-chat/`

## Non-Goals

- No automatic provider retry.
- No increase to the 120-second provider deadline.
- No automatic document mutation, save, upload, indexing or publication.
- No provider key or raw provider diagnostic in the browser.
