# ChatGPT shared-chat snapshot import

## Current Behavior

The governed `/chat` workspace can create local graph-, document-, node-, pillar-, gap- and
change-set-scoped sessions. It cannot start from a public ChatGPT shared conversation, and a
ChatGPT share URL has no supported relationship to the locally persisted session history.

## Target Behavior

A researcher can paste an official public `https://chatgpt.com/share/<conversation-id>` URL into
`/chat`. The API downloads one bounded public HTML snapshot without user credentials or login
cookies, extracts only visible user and assistant text, stores the snapshot messages plus
provenance in PostgreSQL, and creates an
independent active local graph chat. Later turns use the existing provider-neutral governed chat
loop and never update the source ChatGPT conversation.

Visible message text renders as sanitized GitHub-flavored Markdown. When the public snapshot
contains an allowlisted OpenAI HTTPS image or a generated-image `sediment://file_*` pointer exposed
through ChatGPT's anonymous share asset endpoint, the importer validates and caches the bounded
raster bytes locally. The UI renders the same-origin cached image lazily with no referrer. Media
remains separate from provider history so local continuation never sends signed URLs or object keys
to the AI provider.

The UI labels the session as imported, distinguishes imported messages from locally created turns,
links back to the public source, and explains that re-importing creates another snapshot rather than
synchronizing either direction.

## Affected Users

- Owners and researchers importing public ChatGPT context into the Research System.
- Viewers reading an already-imported local session.

## Affected Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `Docs/Research System Implementation Plan.md`
- `README.md`
- `docs/decisions/0022-chatgpt-shared-snapshot-fork.md`

## Non-Goals

- Accessing private ChatGPT conversations or using ChatGPT login/session cookies.
- Continuing the same ChatGPT conversation ID or writing messages back to ChatGPT.
- Importing hidden system instructions, reasoning, raw tool internals, attachments or images that
  the public anonymous share endpoint does not expose.
- Automatic background synchronization or bulk harvesting of shared links.
