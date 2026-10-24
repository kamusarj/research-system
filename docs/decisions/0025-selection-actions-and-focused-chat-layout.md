# 0025 Selection Actions Preserve Explicit Submission and Focused Chat Layout

Date: 2026-08-02

## Status

Accepted

## Context

Browser selection in Brainstorm chat exposes no useful application action, while the document AI
toolbar is detached from long-text selections. The chat desktop layout also spends one full column
on context/tool summaries duplicated by the thread header and message-level proposal links.

## Decision

Use contextual, viewport-clamped selection popovers in document source and chat messages. Document
actions keep the existing persisted proposal plus explicit Accept boundary. Chat actions only
prepare a bounded quoted instruction in the local composer and require explicit Send; they never
mutate history or transmit on selection.

Remove the chat right rail. Keep scope/provider/status as compact thread metadata and keep knowledge
change review links inside the messages that created them. Use a two-column desktop layout with the
conversation as the flexible primary surface and collapse to one column on smaller viewports.

## Alternatives Considered

1. Auto-send a selected chat action: rejected because selection alone is not transmission consent.
2. Keep three columns but shrink the right rail: rejected because its information is duplicated and
   the remaining width still harms normal Windows laptop layouts.
3. Add floating actions only in chat: rejected because the existing document toolbar has the same
   discoverability problem in long source.

## Consequences

Positive:

- Selected-text actions appear where users look and remain reviewable before any durable mutation.
- Conversation width and vertical working space improve on common Windows browser sizes.
- Removing redundant status/debug surfaces reduces visual noise without hiding proposal review.

Tradeoffs:

- Tool-call diagnostics leave the product UI and remain available only through persisted message
  metadata/API and operational tooling.
- Chat quote shortcuts are composer templates rather than provider-specific selection APIs.

## Follow-Up

- Consider a dedicated diagnostics drawer only if operators demonstrate a recurring UI need.

