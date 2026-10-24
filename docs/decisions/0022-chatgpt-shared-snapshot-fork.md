# 0022 One-way ChatGPT shared snapshot forks

Date: 2026-08-01

## Status

Accepted

## Context

The owner wants to paste a public ChatGPT shared link into the Research System, preserve the shared
conversation, and continue chatting locally without changing ChatGPT. OpenAI documents shared links
as public conversation snapshots and does not expose them as Responses/Conversations API state.
The existing graph chat already keeps PostgreSQL-local history and sends bounded, redacted context
through provider-neutral adapters.

## Decision

Treat a ChatGPT shared link as a one-time external import source, never as a remote conversation
identity. Accept only the official public `https://chatgpt.com/share/<id>` form; retrieve it without
credentials under strict public-network, redirect, content-type, byte, message and character bounds;
persist only visible user/assistant text plus immutable provenance; and create an independent local
graph-scoped session. Every later turn is stored locally and cannot write back to ChatGPT.

The importer excludes system instructions, reasoning, tool internals and assets. Existing chat
redaction, context limits, provider selection, `store=false` behavior where supported, and draft-only
graph proposal governance remain unchanged.

## Alternatives Considered

1. Continue the ChatGPT conversation directly: rejected because a shared ID is not a supported API
   conversation identifier and would violate the local-state boundary.
2. Scrape while authenticated with user cookies: rejected because it expands access to private
   account data and introduces credential handling that the owner did not request.
3. Store only the URL and fetch on every turn: rejected because deleted/updated shares would change
   local history and make continuation non-reproducible.
4. One-way immutable snapshot fork: selected because it matches the requested no-write-back
   behavior and keeps PostgreSQL authoritative.

## Consequences

Positive:

- Users can continue useful shared context in the existing governed chat workspace.
- Deleting or changing the remote share does not alter an already imported local snapshot.
- No ChatGPT credential, cookie or write authority enters the Research System.

Tradeoffs:

- The public share page is not a documented transcript API, so payload-format changes can produce a
  typed parse failure until the bounded parser is updated.
- Imported attachments/images are represented only by omission/placeholders and are not downloaded.
- Very large conversations fail visibly rather than being silently truncated.

## Follow-Up

- Monitor typed parse failures without logging source content.
- Add an explicit paste/export fallback only if real payload changes make link-only import
  unreliable; do not weaken private-access or SSRF controls.

