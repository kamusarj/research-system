# Design

## Domain Model

A browser-only `TextSelectionAction` contains selected plain text, the owning message ID and a
viewport anchor. It is ephemeral and never persisted. Document selections continue using their
server-enforced source version, character range and text hash.

## Application Flow

1. Mouse, touch or keyboard selection is captured only within one eligible text container.
2. A floating popover is clamped to the visible viewport near the selection.
3. Document actions call the existing proposal endpoint; button pointer-down preserves textarea
   selection and no source changes until Accept.
4. Chat Ask AI, Explain or Summarize creates a bounded Markdown quote plus instruction in the local
   composer, focuses it, closes the popover and waits for explicit Send.
5. Escape, outside pointer-down, session change or an empty selection closes the popover.

## Interface Contract

No API changes. Chat selection helpers operate only on the existing local `draft` state and the
existing send route. Document selection helpers reuse existing AI edit proposal routes.

## Data Model

No schema, migration, retention or audit change. Selected chat text is not stored until the user
explicitly sends the prepared composer draft through the current governed chat endpoint.

## UI / Platform Impact

- Reusable fixed popover styling uses viewport-clamped `left/top`, high contrast, keyboard buttons
  and compact labels.
- Chat uses two desktop columns, flexible viewport height, zero fixed message-list max-height and a
  single overflow owner per session/message region.
- Scope, provider and status are compact chips in the thread header. Redundant context, knowledge
  summary and tool activity cards are removed; message-level change-set links remain.
- Below tablet width, history stacks above chat and the popover can horizontally scroll inside its
  own bounded surface without creating page overflow.

## Observability

No new logs, metrics or audit content. Browser selection and unsent composer text remain local.

## Alternatives Considered

1. Send a chat action immediately: rejected because selection should not transmit content without
   explicit user review and Send.
2. Keep the right rail collapsed: rejected because all essential information already fits in the
   thread header or message proposal links, while an extra toggle adds noise.
3. Keep the document toolbar sticky at editor top: rejected because it is easy to miss in long
   content and does not match the requested selection interaction.

