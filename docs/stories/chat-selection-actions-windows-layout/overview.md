# Selected-Text Actions and Focused Windows Chat Layout

## Current Behavior

The document editor detects a textarea selection but renders its action bar at the top of the
editor rather than next to the selected text. Brainstorm chat uses normal browser selection only,
so selecting a passage exposes no product actions. Its three-column desktop layout also reserves a
large right rail for context, knowledge-change and tool-debug cards already represented elsewhere,
leaving the conversation narrow and causing avoidable horizontal scrolling in session history.

## Target Behavior

Selecting editable document source opens a nearby floating AI action popover. Selecting text in one
chat message opens a nearby popover with Ask AI, Explain and Summarize shortcuts. Chat shortcuts
only put a bounded quote and instruction into the composer; they never edit chat history or send a
turn automatically.

Brainstorm chat becomes a focused two-column workspace on desktop: bounded session history plus the
conversation. Scope/provider/status become compact thread metadata, graph proposals stay linked in
their originating messages, and the redundant right rail is removed. The workspace must fit common
Windows desktop/laptop viewports and collapse cleanly on tablet/mobile without document-level
horizontal overflow.

## Affected Users

- Owners and researchers using document AI edits or brainstorming from selected passages.
- Viewers selecting chat text; mutation shortcuts remain unavailable without researcher access.

## Affected Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `Docs/Research System Implementation Plan.md`
- `docs/stories/document-ai-edit-rag/`

## Non-Goals

- Editing or deleting historical chat messages.
- Automatically sending selected chat text to a provider.
- Adding new backend routes, database state or provider tools.
- Removing graph change review links or session scope provenance.

